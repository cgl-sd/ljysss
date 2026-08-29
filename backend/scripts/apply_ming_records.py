#!/usr/bin/env python3
"""把名录并进发布内容库：统一 id、回填年号、按《明史》与维基证据补入缺项。

id 一律改成简体名全拼，不再带 `wiki-`、`cbdb-` 之类来源前缀；改名同时把所有引用到
person_id 的表（栏目、关系、出处、维基全文、明史索引、CBDB 映射）一起改写，
避免出现断链。年号由《明史》本文推出，替掉 1531 条「明代」兜底值。

    backend/.venv/bin/python backend/scripts/apply_ming_records.py --dry-run
    backend/.venv/bin/python backend/scripts/apply_ming_records.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from opencc import OpenCC
from pypinyin import Style, lazy_pinyin

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
CONTENT = BACKEND / "data" / "content"
STAGING = BACKEND / "data" / "staging"

t2s = OpenCC("t2s")

TABLES = ["source", "reign", "person", "event", "event_section", "person_section",
          "content_reference", "person_research", "person_relation", "institution",
          "institution_promotion", "institution_reform", "special_item",
          "person_mingshi", "person_wiki", "person_cbdb"]

REAL_ERAS = ["洪武", "建文", "永乐", "洪熙", "宣德", "正统", "景泰", "天顺", "成化",
             "弘治", "正德", "嘉靖", "隆庆", "万历", "泰昌", "天启", "崇祯",
             "弘光", "隆武", "绍武", "永历"]

# 《明史》列传区块 → 软件六分类
BLOCK_CATEGORY = {
    "后妃": "内廷", "宗室诸王": "封爵", "功臣外戚": "封爵", "阉党佞幸": "内廷",
    "文苑": "文苑", "儒林循吏孝义": "朝臣", "隐逸方技奸臣": "朝臣",
    "明臣": "朝臣", "土司": "封爵", "外国西域": "朝臣",
}
MILITARY = re.compile(r"总督|巡抚|总兵|参将|都督|将军|提督|镇守|经略|征伐|战役|武臣")

# 人物页姓名下方那一行的身份标签，取自《明史》列传区块性质
BLOCK_ROLE = {
    "后妃": "后妃", "宗室诸王": "宗室", "功臣外戚": "功臣", "明臣": "明代官员",
    "阉党佞幸": "宦官", "文苑": "文人", "儒林循吏孝义": "儒臣",
    "隐逸方技奸臣": "明代人物", "土司": "土司", "外国西域": "明代人物",
}


def load(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(table: str, rows: list[dict]) -> None:
    (CONTENT / f"{table}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def canonical(name: str, juan: int) -> str:
    base = "".join(lazy_pinyin(t2s.convert(name).strip(), style=Style.NORMAL))
    return base or f"unnamed-{juan}"


def real_reign(value: str) -> str:
    return next((era for era in REAL_ERAS if era in (value or "")), "")


def birth_of(person: dict) -> str:
    """生卒优先取维基条目里的括号纪年，其次保留库内既有写法。"""
    opening = (person.get("wiki") or {}).get("opening", "") if person.get("wiki") else ""
    match = re.search(r"[（(]\s*(\d{3,4})\s*[—\-–]\s*(\d{3,4}|[?？])", opening)
    if match:
        return f"{match.group(1)}—{match.group(2).replace('？', '?').replace('?', '？')}"
    return ""


def life_text(person: dict) -> tuple[str, str]:
    """生平正文与出处：有明代证据的维基条目为主，明史原文块附在末尾。"""
    wiki = person.get("wiki")
    opening = person["opening"]
    if wiki and wiki["ming"] in ("strong", "weak"):
        body = wiki["opening"].strip()[:2600]
        source = f"出《明史》卷{person['juan']}；维基百科「{wiki['wiki_title']}」"
    else:
        body = opening.strip()[:1200]
        source = f"出《明史》卷{person['juan']}"
    block = f"〔《明史》原文〕\n{opening.strip()[:900]}"
    return f"{body}\n\n{block}", source


# 这些字段是键或外部标识，转字会断掉引用与出处对应，保持原值。
TECHNICAL_FIELDS = {
    "id", "url", "person_id", "from_person_id", "to_person_id", "content_id",
    "source_id", "reign_id", "institution_id", "event_id", "section_key",
    "wiki_title", "page_id", "cbdb_id", "category", "kind",
}


def simplify_tables(tables: dict[str, list[dict]]) -> int:
    """全库一律简体字：展示文本繁转简，技术字段不动。"""

    touched = 0
    for rows in tables.values():
        for row in rows:
            for field, value in list(row.items()):
                if field in TECHNICAL_FIELDS or not isinstance(value, str):
                    continue
                simple = t2s.convert(value)
                if simple != value:
                    row[field] = simple
                    touched += 1
    return touched


def next_position(used: set[tuple[str, str, int]], content_id: str, section: str) -> int:
    position = 0
    while (content_id, section, position) in used:
        position += 1
    used.add((content_id, section, position))
    return position


def main(dry_run: bool) -> None:
    roster = [json.loads(line) for line in (STAGING / "persons.jsonl").read_text(encoding="utf-8").splitlines()
              if line.strip()]
    tables = {name: load(name) for name in TABLES}
    people = tables["person"]

    by_name: dict[str, dict] = {}
    for item in roster:
        by_name.setdefault(t2s.convert(item["name"]), item)

    # 旧 id → 统一 id：按简体名对齐；全库共用一个计数器分配唯一 id，
    # 否则同音不同字（王英 / 王滢 同为 wangying）会跨批相撞。
    taken: Counter[str] = Counter()

    def reserve(name: str) -> str:
        base = "".join(lazy_pinyin(name, style=Style.NORMAL)) or f"unnamed{len(taken)}"
        taken[base] += 1
        return base if taken[base] == 1 else f"{base}-{taken[base]}"

    from app.catalog import PEOPLE as CATALOG_PEOPLE

    # catalog.py 按自身 id 回写种子，改掉这些人的 id 会让启动同步插出同一人物的第二条记录。
    catalog_ids = {person["id"] for person in CATALOG_PEOPLE}
    rename: dict[str, str] = {}
    for person in people:
        simple = t2s.convert(person["name"]).strip()
        if person["id"] in catalog_ids:
            taken[person["id"]] += 1
            new_id = person["id"]
        else:
            new_id = reserve(simple)
        if new_id != person["id"]:
            rename[person["id"]] = new_id
        person["id"] = new_id
        person["name"] = simple

    # 全表改写 id 引用。
    def rewrite(table: str, *fields: str) -> int:
        changed = 0
        for row in tables[table]:
            for field in fields:
                if row.get(field) in rename:
                    row[field] = rename[row[field]]
                    changed += 1
        return changed

    touched = {
        "person_section": rewrite("person_section", "person_id"),
        "person_relation": rewrite("person_relation", "from_person_id", "to_person_id"),
        "content_reference": rewrite("content_reference", "content_id"),
        "person_wiki": rewrite("person_wiki", "person_id"),
        "person_mingshi": rewrite("person_mingshi", "person_id"),
        "person_cbdb": rewrite("person_cbdb", "person_id"),
        "person_research": rewrite("person_research", "person_id"),
    }

    ref_keys = {(r["content_id"], r["section_key"], r["position"])
                for r in tables["content_reference"] if r.get("content_type") == "person"}
    covered = {p["name"] for p in people}
    added = [item for item in roster if t2s.convert(item["name"]) not in covered]
    usable: list[dict] = []
    for item in added:
        wiki = item.get("wiki") or {}
        has_wiki_text = wiki.get("ming") in ("strong", "weak") and wiki.get("chars", 0) >= 200
        # 《明史》本文只有一句「某某，早薨」且无维基正文可用时，建条目只会得到空壳。
        if len(item["opening"].strip()) >= 25 or has_wiki_text:
            usable.append(item)
    too_thin = len(added) - len(usable)
    added = usable
    for item in added:
        name = t2s.convert(item["name"]).strip()
        new_id = reserve(name)
        life, source = life_text(item)
        category = BLOCK_CATEGORY.get(item["block"], "朝臣")
        if category == "朝臣" and MILITARY.search(item["opening"][:300]):
            category = "将帅"
        people.append({
            "id": new_id, "name": name,
            "title": BLOCK_ROLE.get(item["block"], "明代人物"),
            "reign": item.get("era") or "明",
            "years": birth_of(item) or "生卒未详",
            "category": category,
            "courtesy_name": "",
            "summary": item["opening"][:120],
            "biography": life,
            "family_summary": "",
            "source_id": tables["source"][0]["id"] if tables["source"] else "mingshi-editorial-v1",
        })
        tables["person_section"].append({"person_id": new_id, "section_key": "life",
                                         "title": "生平", "position": 0, "content": life})
        wiki = item.get("wiki") or {}
        tables["content_reference"].append({
            "content_type": "person", "content_id": new_id, "section_key": "life",
            "position": next_position(ref_keys, new_id, "life"),
            "title": f"《明史》卷{item['juan']}·{item['block']}"
                     + (f"；维基百科「{wiki['wiki_title']}」" if wiki else ""),
            "url": wiki.get("url", ""),
            "locator": f"明史卷{item['juan']:03d}",
            "note": {"strong": "维基条目含明代年号或明代纪年", "weak": "维基条目仅泛称明",
                     "none": "维基条目无明代证据，正文只取《明史》", None: "无维基条目"}[
                        wiki.get("ming") if wiki else None],
        })

    # 既有人物里本就是《明史》传主的，补上出处锚点——此前库里 1453 人零出处。
    anchored = {row["content_id"] for row in tables["content_reference"]
                if row.get("content_type") == "person" and str(row.get("locator", "")).startswith("明史卷")}
    existing_anchors = 0
    for person in people:
        entry = by_name.get(person["name"])
        if not entry or person["id"] in anchored:
            continue
        wiki = entry.get("wiki") or {}
        tables["content_reference"].append({
            "content_type": "person", "content_id": person["id"], "section_key": "life",
            "position": next_position(ref_keys, person["id"], "life"),
            "title": f"《明史》卷{entry['juan']}·{entry['block']}"
                     + (f"；维基百科「{wiki['wiki_title']}」" if wiki else ""),
            "url": wiki.get("url", ""),
            "locator": f"明史卷{entry['juan']:03d}",
            "note": "名录比对：姓名与《明史》列传卷次对应",
        })
        existing_anchors += 1

    # 年号回填：兜底值一律换成《明史》本文推出的年号。
    filled = 0
    for person in people:
        if real_reign(person.get("reign", "")):
            continue
        entry = by_name.get(person["name"])
        era = (entry or {}).get("era") or ""
        if era:
            person["reign"] = era
            filled += 1

    print(f"改名 {len(rename)} 条（含去掉 wiki- 前缀与繁体转简体）")
    print(f"名录补入 {len(added)} 人（另有 {too_thin} 条《明史》本文不足 25 字且无维基正文，不建空壳）；库内人物 {len(people)}")
    print(f"既有人物补登明史锚点 {existing_anchors} 条")
    print(f"年号回填 {filled} 条；仍无真年号 {sum(1 for p in people if not real_reign(p['reign']))} 条")
    print(f"新人物分类分布：{dict(Counter(p['category'] for p in people))}")
    simplified = simplify_tables(tables)
    print(f"全表简体化：改写 {simplified} 个字段值")
    print("引用改写：", {k: v for k, v in touched.items() if v})
    if dry_run:
        print("\n[dry-run] 未写入。")
        return

    (STAGING / "id_map.json").write_text(json.dumps(rename, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, rows in tables.items():
        dump(name, rows)
    print("\n已写入 data/content/*.jsonl；执行 content_store.py import 重建库并跑后端测试。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
