#!/usr/bin/env python3
"""留下的人物必须同时满足两条：有维基百科条目，且读简介能确认是明代人。

判据一（有条目）：content_reference 里有指向维基条目的 url，或 person_wiki 存着该
条目的条目名与全文（早期批量入库只没登记出处而已）。

判据二（是明代人），按简介文字判：
1. 简介自报他朝身份（「西汉…将领」「南宋…名臣」）→ 判否。这类条目讲的是同名他人，
   即便《明史》另有同名传主，这一行也不是明人。
2. 简介含明代年号，或含「明」且带 1300—1700 年数字 → 判是。
3. 简介没有明代信号，但《明史》有传、或年号属明、或生卒落在明代 → 作为例外保留。

连带清理：栏目、亲属、关系边、出处登记、维基全文、明史索引、CBDB 映射、检索台账、
事件参与人、编年参与人；事件表的 participants 姓名串同步剔除。

    backend/.venv/bin/python backend/scripts/prune_to_wikipedia.py --dry-run
    backend/.venv/bin/python backend/scripts/prune_to_wikipedia.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"
STAGING = BACKEND / "data" / "staging"
sys.path.insert(0, str(BACKEND))

ERAS = ("洪武", "建文", "永乐", "洪熙", "宣德", "正统", "景泰", "天顺", "成化", "弘治", "正德",
        "嘉靖", "隆庆", "万历", "泰昌", "天启", "崇祯", "弘光", "隆武", "绍武", "永历")
OTHER_DYNASTY = re.compile(
    r"(西汉|东汉|南宋|北宋|秦朝|汉朝|晋朝|隋朝|唐朝|唐代|宋代|宋朝|元代|元朝|三国|清朝|清代)"
    r"[^\n，。]{0,14}?(?:将领|名臣|大臣|皇帝|政治家|学者|官员|人物|宗室|宰相|进士|诗人|外戚|画家|书法家)")
MING_MARK = re.compile(r"(明朝|明代|明初|明末|明中叶|元末明初|明太祖|明成祖|明代宗室|朱元璋|洪武)")
YEAR_IN_MING = re.compile(r"\b(1[3-6]\d{2})\b")
BORN = re.compile(r"^\s*(\d{4})—")

# 表名 → 该表里指向 person.id 的列
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
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def judge_ming(person: dict, intro: str) -> str:
    """读简介判朝代：yes / no / unknown。"""

    head = intro[:260]
    other = OTHER_DYNASTY.search(head)
    if other and not MING_MARK.search(head):
        return "no"
    # 消歧义/重定向页说明正文取错了条目，但人未必不是明人——交旁证判
    if re.search(r"可以指|可以是|可能指|（消歧义）", head):
        return "unknown"
    if any(era in head for era in ERAS):
        return "yes"
    if MING_MARK.search(head) and any(1300 <= int(y) <= 1700 for y in YEAR_IN_MING.findall(head)):
        return "yes"
    return "unknown"


def purge_seeds(doomed: set[str]) -> None:
    """删掉的人必须同时从 catalog.py 移除，否则服务启动的种子回写会把他们插回来。"""

    path = BACKEND / "app" / "catalog.py"
    lines = path.read_text(encoding="utf-8").split("\n")
    # 种子有三种格式，各自精确匹配，避免误删正文里恰好提到该 id 的行
    people_line = re.compile(r"^\s*(\"|')(?P<pid>[a-z0-9\-]+)(\"|')?\|")
    dict_line = re.compile(r'^\s*"(?P<pid>[a-z0-9\-]+)"\s*:\s*"')
    dropped = 0
    kept = []
    for line in lines:
        pid = ""
        if "|" in line and not line.strip().startswith("#"):
            match = re.match(r"^\s*([a-z0-9\-]+)\|", line)
            pid = match.group(1) if match else ""
        if not pid:
            match = dict_line.match(line)
            pid = match.group("pid") if match else ""
        if not pid:
            # 关系边与画像键：整行里出现被删 id 的引号形式
            quoted = re.findall(r"['\"]([a-z0-9\-]+)['\"]", line)
            pid = next((token for token in quoted if token in doomed), "")
        if pid in doomed:
            dropped += 1
            continue
        kept.append(line)
    path.write_text("\n".join(kept), encoding="utf-8")
    print(f"catalog.py 同步移除 {dropped} 行种子记录（防止启动回写复活）")


def main(dry_run: bool) -> None:
    people = load("person")
    refs = load("content_reference")
    wiki = load("person_wiki")
    url_ids = {r["content_id"] for r in refs
               if r.get("content_type") == "person" and r.get("url")}
    titled = {r["person_id"]: r["wiki_title"] for r in wiki if r.get("wiki_title")}
    wiki_text = {r["person_id"]: r.get("full_text", "") for r in wiki}
    backfilled = sorted(set(titled) - url_ids)
    has_article = url_ids | set(titled)

    rolls = {json.loads(line)["name"] for line in
             (STAGING / "persons.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()} \
        if (STAGING / "persons.jsonl").exists() else set()
    anchored = {r["content_id"] for r in refs
                if r.get("content_type") == "person" and str(r.get("locator", "")).startswith("明史卷")}

    reasons: Counter[str] = Counter()
    rewrite_needed: list[str] = []  # 保留占位以兼容下方打印
    doomed: set[str] = set()
    for person in people:
        pid = person["id"]
        if pid not in has_article:
            reasons["无维基条目"] += 1
            doomed.add(pid)
            continue
        intro_head = (wiki_text.get(pid) or person.get("biography", ""))[:260]
        if re.search(r"可以指|可以是|可能指|（消歧义）", intro_head):
            # 解析过一轮仍是消歧义页，说明拿不到属于他本人的条目正文，按标准不保留
            reasons["正文仍是消歧义页"] += 1
            doomed.add(pid)
            continue
        intro = (wiki_text.get(pid) or person.get("biography", "") or person.get("summary", ""))[:600]
        verdict = judge_ming(person, intro)
        if verdict == "no":
            reasons["简介自报他朝身份"] += 1
            doomed.add(pid)
        elif verdict == "unknown" and not (pid in anchored or person["name"] in rolls
                                           or any(era in (person.get("reign") or "") for era in ERAS)
                                           or (BORN.match(person.get("years") or "")
                                               and 1300 <= int(BORN.match(person["years"]).group(1)) <= 1660)):
            reasons["简介无明代信号且无旁证"] += 1
            doomed.add(pid)

    keep = len(people) - len(doomed)
    print(f"人物 {len(people)} → 保留 {keep}，删除 {len(doomed)}")
    for reason, count in reasons.most_common():
        print(f"  {reason:<22} {count}")
    print(f"  （其中 {len(backfilled)} 人只有全文存档，补登记维基出处后保留）")
    print(f"  正文是消歧义页、需换条目的：{len(rewrite_needed)} 人 例：{'、'.join(rewrite_needed[:8])}")

    # 出处登记有 UNIQUE(类型, 对象, 栏目, 位次)，补登记要取该人物该栏目的下一个空位
    used_positions = {(r["content_type"], r["content_id"], r["section_key"], r["position"]) for r in refs}

    def free_position(kind: str, cid: str, section: str) -> int:
        position = 0
        while (kind, cid, section, position) in used_positions:
            position += 1
        used_positions.add((kind, cid, section, position))
        return position

    for pid in backfilled:
        title = titled[pid]
        refs.append({"content_type": "person", "content_id": pid, "section_key": "life",
                     "position": free_position("person", pid, "life"),
                     "title": f"维基百科「{title}」",
                     "url": "https://zh.wikipedia.org/wiki/" + title.replace(" ", "_"),
                     "locator": "", "note": "由全文存档补登记出处"})

    doomed_names = {p["name"] for p in people if p["id"] in doomed}
    tables = {name: load(name) for name in CASCADE}
    report: dict[str, int] = {}
    for table, fields in CASCADE.items():
        before = len(tables[table])
        tables[table] = [row for row in tables[table]
                         if not any(row.get(field) in doomed for field in fields)]
        report[table] = before - len(tables[table])

    events = load("event")
    for event in events:
        names = [n.strip() for n in (event.get("participants") or "").split("、") if n.strip()]
        event["participants"] = "、".join(n for n in names if n not in doomed_names)
    refs = [r for r in refs if not (r.get("content_type") == "person" and r.get("content_id") in doomed)]

    print("级联删除：" + "｜".join(f"{k} {v}" for k, v in report.items() if v))
    if dry_run:
        print("\n[dry-run] 未写入。")
        return
    for name, rows in tables.items():
        dump(name, rows)
    dump("person", [p for p in people if p["id"] not in doomed])
    dump("event", events)
    dump("content_reference", refs)
    purge_seeds(doomed)
    print(f"已写入：人物余 {keep} 人")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
