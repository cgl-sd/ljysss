#!/usr/bin/env python3
"""将已核对身份的明人改指到正确的中文维基百科条目。

同名页曾把《明史》中的明人接到汉、唐、清等同名者，或接到王爵消歧义页。本脚本
只处理下方逐条比对过姓名、字、官历或家世的十个目标；它会更新维基正文、出处链接和
「生平」首段，不改变人物的其他栏目。不能从离线维基包取到目标页时立即退出，不写入。

    backend/.venv/bin/python backend/scripts/repair_person_wikipedia_sources.py --dry-run
    backend/.venv/bin/python backend/scripts/repair_person_wikipedia_sources.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from resolve_disambiguation import fetch_titles  # noqa: E402


# key 是库内稳定 id，value 是经正文身份字段确认的维基条目标题。不能把仅同名的页加入这里。
TARGETS = {
    "fengquan": "冯铨",
    "mahuanghou": "孝慈高皇后 (明朝)",
    "zhuyoubin": "朱祐槟",
    "wangweizhen": "王維楨 (明朝)",
    "zhaorong": "趙榮 (工部尚書)",
    "wangyuan-3": "王淵 (明朝)",
    "zhangsheng": "張昇 (狀元)",
    "linjun": "林俊 (明朝)",
    "yangsong": "楊松 (嘉靖進士)",
    "lichanggeng": "李長庚 (明朝)",
    "luqian": "盧謙 (明朝)",
    "xuzhonghang": "徐中行 (嘉靖進士)",
    "lizhen": "李楨 (隆慶進士)",
    "xuwenhua": "徐文华 (正德进士)",
}

t2s = OpenCC("t2s")
WIKI_NOISE = re.compile(r"^(?:==+[^=]+==+|\{\{[^}]*\}\}|参考資料|外部連結|外部链接|注釋|注释|參見|参见|维基|Wiki).*$")


def load(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(table: str, rows: list[dict]) -> None:
    (CONTENT / f"{table}.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )


def clean_wiki(text: str) -> str:
    lines = []
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line or WIKI_NOISE.match(line) or line.startswith(("!", "#", "*", ":", ";", "==")):
            continue
        line = t2s.convert(re.sub(r"\[\d+\]|\[[a-z]\]|\{\{[^}]*\}\}|<[^>]+>", "", line)).strip()
        if len(line) >= 8:
            lines.append(line)
    return "\n".join(lines)


def is_wikipedia_reference(row: dict) -> bool:
    return "zh.wikipedia.org" in (row.get("url") or "") or "维基" in (row.get("title") or "")


def mingshi_block(content: str) -> str:
    marker = "〔《明史》原文〕"
    index = (content or "").find(marker)
    return (content[index:].strip() if index >= 0 else "")


def next_position(refs: list[dict], person_id: str) -> int:
    used = {
        row.get("position", 0)
        for row in refs
        if row.get("content_type") == "person" and row.get("content_id") == person_id
        and row.get("section_key") == "life"
    }
    position = 0
    while position in used:
        position += 1
    return position


def main(dry_run: bool) -> None:
    fetched = fetch_titles(set(TARGETS.values()))
    missing = sorted(set(TARGETS.values()) - set(fetched))
    if missing:
        raise SystemExit(f"离线维基包未找到目标条目：{'、'.join(missing)}")

    people = {row["id"] for row in load("person")}
    unknown = sorted(set(TARGETS) - people)
    if unknown:
        raise SystemExit(f"内容库不存在目标人物：{'、'.join(unknown)}")

    wiki = {row["person_id"]: row for row in load("person_wiki")}
    refs = load("content_reference")
    sections = load("person_section")
    life_by_id = {row["person_id"]: row for row in sections if row["section_key"] == "life"}

    removed_refs = 0
    for person_id, target in TARGETS.items():
        hit = fetched[target]
        wiki[person_id] = {
            "person_id": person_id,
            "wiki_title": hit["wiki_title"],
            "full_text": hit["full_text"],
        }
        retained_refs = []
        for row in refs:
            if row.get("content_type") != "person" or row.get("content_id") != person_id:
                retained_refs.append(row)
                continue
            if not is_wikipedia_reference(row):
                retained_refs.append(row)
                continue
            if "明史" in (row.get("title") or "") or "明史" in (row.get("locator") or ""):
                # 原来一条记录同时承载两种来源时，拆出《明史》定位，维基改为单独一条。
                row = dict(row)
                row["title"] = row["title"].split("；", 1)[0]
                row["url"] = ""
                retained_refs.append(row)
            else:
                removed_refs += 1
        refs = retained_refs
        refs.append({
            "content_type": "person",
            "content_id": person_id,
            "section_key": "life",
            "position": next_position(refs, person_id),
            "title": f"维基百科「{hit['wiki_title']}」",
            "url": hit["url"],
            "locator": hit["wiki_title"],
            "note": "同名条目经身份字段核对后改指此页",
        })

        body = clean_wiki(hit["full_text"])
        original = life_by_id.get(person_id, {}).get("content", "")
        original_block = mingshi_block(original)
        if original_block:
            body = f"{body}\n\n{original_block}"
        life_by_id[person_id] = {
            "person_id": person_id,
            "section_key": "life",
            "title": "生平",
            "position": 0,
            "content": body,
        }

    updated_sections = [row for row in sections if row["section_key"] != "life" or row["person_id"] not in TARGETS]
    updated_sections.extend(life_by_id[person_id] for person_id in TARGETS)

    print(f"已核对并改指 {len(TARGETS)} 人的维基来源；替换旧维基出处 {removed_refs} 条。")
    for person_id, target in TARGETS.items():
        print(f"  {person_id} → {fetched[target]['wiki_title']}")
    if dry_run:
        print("[dry-run] 未写入。")
        return

    dump("person_wiki", list(wiki.values()))
    dump("content_reference", refs)
    dump("person_section", updated_sections)
    print("已写入 person_wiki、content_reference 与对应生平栏目。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
