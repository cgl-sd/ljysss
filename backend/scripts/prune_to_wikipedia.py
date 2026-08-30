#!/usr/bin/env python3
"""删除不满足中文维基百科明朝人物门槛的内容记录。

保留条件必须同时成立：维基正文可识别为库内这个人，且正文明确为明朝（含南明）人物。
同名但属于他朝、现代人物、地名、制度或泛概念的页面不能作为人物资料。判定由
``audit_person_existence.py`` 集中完成；本脚本只按其 ``confirmed`` 结果执行级联清理，
不会凭《明史》卷次、年号或百度来源绕过该门槛。

还会为已有 ``person_wiki`` 正文而缺少链接的保留人物补登记官方维基 URL。

    backend/.venv/bin/python backend/scripts/prune_to_wikipedia.py --dry-run
    backend/.venv/bin/python backend/scripts/prune_to_wikipedia.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, urlparse

BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_person_existence import audit  # noqa: E402


# 表名 → 指向 person.id 的列。删人时必须清除所有直接或反向关联。
CASCADE = {
    "person_section": ["person_id"],
    "person_kin": ["person_id", "kin_person_id"],
    "person_relation": ["from_person_id", "to_person_id"],
    "person_wiki": ["person_id"],
    "person_mingshi": ["person_id"],
    "person_cbdb": ["person_id"],
    "person_research": ["person_id"],
    "event_participant": ["person_id"],
    "annal_participant": ["person_id"],
}


def load(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] \
        if path.exists() else []


def dump(table: str, rows: list[dict]) -> None:
    (CONTENT / f"{table}.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )


def is_wikipedia_url(url: str) -> bool:
    return urlparse(url or "").netloc == "zh.wikipedia.org"


def wikipedia_url(title: str) -> str:
    return "https://zh.wikipedia.org/wiki/" + quote((title or "").replace(" ", "_"))


def free_position(refs: list[dict], content_id: str) -> int:
    used = {
        row.get("position", 0)
        for row in refs
        if row.get("content_type") == "person" and row.get("content_id") == content_id
        and row.get("section_key") == "life"
    }
    position = 0
    while position in used:
        position += 1
    return position


def purge_seeds(doomed: set[str]) -> int:
    """同步删 catalog.py 的对应种子，防止服务启动回写复活已移除人物。"""

    path = BACKEND / "app" / "catalog.py"
    lines = path.read_text(encoding="utf-8").split("\n")
    dict_line = re.compile(r'^\s*"(?P<pid>[a-z0-9\-]+)"\s*:\s*"')
    dropped = 0
    kept = []
    for line in lines:
        person_id = ""
        if "|" in line and not line.strip().startswith("#"):
            match = re.match(r"^\s*([a-z0-9\-]+)\|", line)
            person_id = match.group(1) if match else ""
        if not person_id:
            match = dict_line.match(line)
            person_id = match.group("pid") if match else ""
        if not person_id:
            quoted = re.findall(r"['\"]([a-z0-9\-]+)['\"]", line)
            person_id = next((value for value in quoted if value in doomed), "")
        if person_id in doomed:
            dropped += 1
            continue
        kept.append(line)
    path.write_text("\n".join(kept), encoding="utf-8")
    return dropped


def main(dry_run: bool) -> None:
    _, results, profiles = audit(fetch_missing=True, include_profiles=True)
    confirmed = {row["id"] for row in results if row["status"] == "confirmed"}
    people = load("person")
    person_ids = {person["id"] for person in people}
    if confirmed - person_ids:
        raise SystemExit("审计结果与内容库不一致，拒绝删除")
    doomed = person_ids - confirmed

    print(f"人物 {len(people)} → 保留 {len(confirmed)}，删除 {len(doomed)}")
    for reason in sorted({row["reason"] for row in results if row["id"] in doomed}):
        count = sum(row["reason"] == reason for row in results if row["id"] in doomed)
        print(f"  {reason} {count}")

    tables = {name: load(name) for name in CASCADE}
    report: dict[str, int] = {}
    for table, fields in CASCADE.items():
        before = len(tables[table])
        tables[table] = [
            row for row in tables[table]
            if not any(row.get(field) in doomed for field in fields)
        ]
        report[table] = before - len(tables[table])

    # 人名字符串只能在该名字的全部 id 都被删除时剔除，不能因同名重复记录误删保留者。
    ids_by_name: dict[str, set[str]] = defaultdict(set)
    for person in people:
        ids_by_name[person["name"]].add(person["id"])
    doomed_names = {name for name, ids in ids_by_name.items() if ids <= doomed}
    events = load("event")
    for event in events:
        names = [name.strip() for name in (event.get("participants") or "").split("、") if name.strip()]
        event["participants"] = "、".join(name for name in names if name not in doomed_names)

    refs = [
        row for row in load("content_reference")
        if not (row.get("content_type") == "person" and row.get("content_id") in doomed)
    ]
    result_by_id = {row["id"]: row for row in results}
    # audit 为早期未缓存的记录按标题读取了离线维基包；将通过门槛的原文一并落入
    # person_wiki，避免下一次只因缓存缺失而重复扫描或失去可复核正文。
    wiki_by_person = {row["person_id"]: row for row in tables["person_wiki"]}
    for person_id in sorted(confirmed - set(wiki_by_person)):
        profile = profiles.get(person_id, {})
        title = profile.get("wiki_title", "")
        text = profile.get("full_text", "")
        if not title or not text:
            raise SystemExit(f"保留人物 {person_id} 缺少可写入的维基正文")
        row = {"person_id": person_id, "wiki_title": title, "full_text": text}
        tables["person_wiki"].append(row)
        wiki_by_person[person_id] = row
    backfilled = 0
    for person_id in sorted(confirmed):
        if any(
            row.get("content_type") == "person" and row.get("content_id") == person_id
            and is_wikipedia_url(row.get("url", ""))
            for row in refs
        ):
            continue
        wiki = wiki_by_person.get(person_id)
        if not wiki or not wiki.get("wiki_title"):
            raise SystemExit(f"保留人物 {person_id} 缺少可登记的维基条目")
        refs.append({
            "content_type": "person",
            "content_id": person_id,
            "section_key": "life",
            "position": free_position(refs, person_id),
            "title": f"维基百科「{wiki['wiki_title']}」",
            "url": wikipedia_url(wiki["wiki_title"]),
            "locator": wiki["wiki_title"],
            "note": "由已核对的离线维基正文补登记出处",
        })
        backfilled += 1

    print("级联删除：" + "｜".join(f"{table} {count}" for table, count in report.items() if count))
    print(f"补登记中文维基出处：{backfilled} 条")
    if dry_run:
        print("[dry-run] 未写入。")
        return

    for table, rows in tables.items():
        dump(table, rows)
    dump("person", [person for person in people if person["id"] not in doomed])
    dump("event", events)
    dump("content_reference", refs)
    seed_count = purge_seeds(doomed)
    print(f"catalog.py 同步移除 {seed_count} 行种子记录；已写入人物余 {len(confirmed)} 人。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
