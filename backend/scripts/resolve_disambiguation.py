#!/usr/bin/env python3
"""把消歧义页换成真正的明代条目：解析同名列表 → 选出明代那一条 → 回维基包取正文。

批量入库时按标题精确命中，撞上消歧义页的人就存成了一串「某某可以指：…」，
正文不是这个人。好在消歧义页本身写着目标条目名与一句说明，形如：

    刘基可以指：
    刘基 (西汉)，西汉河间刚王
    刘伯温，明初政治家          ← 目标

取说明里带明代年号或「明」字的那一行，其条目前半段就是目标标题；再用一次
维基包扫描按标题（含简繁两种写法）取回正文，覆盖 person_wiki 与出处登记。

    backend/.venv/bin/python backend/scripts/resolve_disambiguation.py --dry-run
    backend/.venv/bin/python backend/scripts/resolve_disambiguation.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq
from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
CONTENT = BACKEND / "data" / "content"
PACKS = [BACKEND / "sources" / "wikipedia_zh" / f"train-0000{i}.parquet" for i in range(6)]

t2s = OpenCC("t2s")
s2t = OpenCC("s2t")

DISAMBIG_HEAD = re.compile(r"^(.{1,12}?)(?:可以指|可以是|可能指|是下列|为下列)")
ENTRY = re.compile(r"^(.+?)\s*[，,]\s*(.{2,60})$")
ERAS = ("洪武", "建文", "永乐", "洪熙", "宣德", "正统", "景泰", "天顺", "成化", "弘治", "正德",
        "嘉靖", "隆庆", "万历", "泰昌", "天启", "崇祯", "弘光", "隆武", "绍武", "永历")
MING_HINT = re.compile(r"明[朝代初末宗室]?|南明|" + "|".join(ERAS))
NOT_MING = re.compile(r"西汉|东汉|南宋|北宋|唐[高祖]?|朝鲜|清末|清朝|民国|中华人民共和国|台湾|日本")


def load(table: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(table: str, rows: list[dict]) -> None:
    (CONTENT / f"{table}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def pick_target(text: str) -> str:
    """从消歧义页里挑出说明指向明代的那一条目标标题。"""

    for line in text.split("\n"):
        line = line.strip(" *:\u3000")
        if not line or DISAMBIG_HEAD.match(line) or "消歧义" in line:
            continue
        match = ENTRY.match(line)
        if not match:
            continue
        title, note = match.group(1).strip(), match.group(2)
        title = title.strip("（(").strip()
        if MING_HINT.search(note) and not NOT_MING.search(note):
            # 消歧义页常给目标加「(明朝)」这类后缀，而真正的条目名可能没有它，
            # 也可能没有别的同名者却仍带后缀。两种写法都留作候选。
            bare = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", title).strip()
            return "\u0000".join(dict.fromkeys([title, bare])) if bare != title else title
    return ""


def fetch_titles(wanted: set[str]) -> dict[str, dict]:
    """按简繁两种写法扫维基包，取回目标条目的正文。"""

    lookup: dict[str, str] = {}
    for title in wanted:
        lookup.setdefault(title, title)
        lookup.setdefault(s2t.convert(title), title)
        lookup.setdefault(t2s.convert(title), title)
    hits: dict[str, dict] = {}
    for pack in PACKS:
        reader = pq.ParquetFile(str(pack))
        for batch in reader.iter_batches(columns=["id", "title", "url", "text"], batch_size=4096):
            titles = batch.column("title").to_pylist()
            ids = batch.column("id").to_pylist()
            urls = batch.column("url").to_pylist()
            texts = batch.column("text").to_pylist()
            for index, title in enumerate(titles):
                key = lookup.get(title.strip())
                if key and key not in hits:
                    hits[key] = {"wiki_title": title, "page_id": ids[index], "url": urls[index],
                                 "full_text": texts[index] or ""}
    return hits


def main(dry_run: bool) -> None:
    wiki = {row["person_id"]: row for row in load("person_wiki")}
    people = {p["id"]: p for p in load("person")}
    targets: dict[str, list[str]] = {}
    wanted_titles: set[str] = set()
    for person_id, row in wiki.items():
        text = row.get("full_text", "")
        if not DISAMBIG_HEAD.match(text.strip()):
            continue
        picked = pick_target(text)
        if picked:
            candidates = picked.split("\u0000")
            targets[person_id] = candidates
            wanted_titles.update(candidates)
    print(f"消歧义页人物中可解析出明代目标条目的：{len(targets)} 人（共 {sum(1 for r in wiki.values() if DISAMBIG_HEAD.match((r.get('full_text') or '').strip()))} 人是消歧义页）")
    unresolved = [people[pid]["name"] for pid in wiki
                  if DISAMBIG_HEAD.match((wiki[pid].get("full_text") or "").strip()) and pid not in targets]
    print(f"解析不出明代目标的 {len(unresolved)} 人，例：{'、'.join(unresolved[:12])}")
    if not targets:
        return

    print("扫描维基包取正文…")
    fetched = fetch_titles(wanted_titles)
    print(f"命中 {len(fetched)} / {len(wanted_titles)} 个候选标题")

    refs = load("content_reference")
    url_of = {r["content_id"]: r for r in refs
              if r.get("content_type") == "person" and r.get("url") and r.get("section_key") == "life"}
    changed = 0
    for person_id, candidates in targets.items():
        hit = next((fetched.get(title) for title in candidates if title in fetched), None)
        if not hit:
            continue
        wiki[person_id]["wiki_title"] = hit["wiki_title"]
        wiki[person_id]["full_text"] = hit["full_text"]
        url = hit["url"]
        if person_id in url_of:
            url_of[person_id]["url"] = url
            url_of[person_id]["title"] = f"维基百科「{hit['wiki_title']}」"
        else:
            refs.append({"content_type": "person", "content_id": person_id, "section_key": "life",
                         "position": 0, "title": f"维基百科「{hit['wiki_title']}」", "url": url,
                         "locator": "", "note": "消歧义页解析后补登记"})
        changed += 1
    print(f"已替换正文来源：{changed} 人；仍取不到的 {len(targets) - changed} 人")
    if dry_run:
        print("\n[dry-run] 未写入。")
        return
    dump("person_wiki", list(wiki.values()))
    dump("content_reference", refs)
    print("已写入 person_wiki 与 content_reference；接着重跑 build_person_static_sections 生成生平")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
