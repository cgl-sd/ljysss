#!/usr/bin/env python3
"""把维基数据亲属声明与百度百科名片结构化写入 person_relation。

数据来源：
- person_research 中已完成维基数据匹配的实体：P22 父亲、P25 母亲、
  P26 配偶、P40 子女、P3373 兄弟姐妹；
- 百度百科开放接口名片：父亲 / 母亲 / 配偶 / 儿子 字段（按姓名反查库内人物）。

写入规则：
- 仅当亲属对象同样是库内人物才建关系；库外亲属保留在“家族与子嗣”栏目。
- 关系类型：父子 / 母子 / 配偶 / 兄弟姐妹，与 App 端 RelationshipType
  标签一一对应；兄弟姐妹只按 id 较小的一方写入，避免双向重复。
- 皇帝的宗室家庭关系允许建立；皇帝与文臣武将的臣属关系仍被禁止。
- INSERT OR IGNORE：不覆盖人工编目的既有关系。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import connect, initialize_database  # noqa: E402
from enrich_people_from_wikidata import entity_data, entity_ids  # noqa: E402

KINSHIP_PROPERTIES = {
    "P22": ("father", "父子"),
    "P25": ("mother", "母子"),
    "P26": ("spouse", "配偶"),
    "P40": ("child", "父子"),
    "P3373": ("sibling", "兄弟姐妹"),
}
BAIKE_API = "https://baike.baidu.com/api/openapi/BaikeLemmaCardApi"
BAIKE_KINSHIP_FIELDS = {"父亲": "father", "母亲": "mother", "配偶": "spouse", "皇后": "spouse", "儿子": "child"}
TAG_PATTERN = re.compile(r"<[^>]+>")


def baike_card(name: str) -> dict[str, list[str]]:
    url = f"{BAIKE_API}?scope=103&format=json&appid=379020&bk_length=400&bk_key={quote(name)}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    try:
        with urlopen(request, timeout=15) as response:
            data = json.load(response)
    except Exception:
        return {}
    if data.get("title") != name:
        return {}
    result: dict[str, list[str]] = {}
    for item in data.get("card", []):
        field = TAG_PATTERN.sub("", item.get("name", "")).strip()
        values = [TAG_PATTERN.sub("", value).strip() for value in item.get("value", [])]
        values = [value for value in values if value]
        if field in BAIKE_KINSHIP_FIELDS and values:
            result.setdefault(BAIKE_KINSHIP_FIELDS[field], []).extend(values)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="结构化补录维基数据与百度百科亲属关系")
    parser.add_argument("--dry-run", action="store_true", help="只打印将写入的关系，不写库")
    parser.add_argument("--skip-baike", action="store_true", help="跳过百度百科名片来源")
    args = parser.parse_args()

    initialize_database()
    with connect() as db:
        rows = db.execute(
            """
            SELECT person_id, entity_id FROM person_research
            WHERE status = 'matched' AND entity_id <> '' AND provider IN ('wikidata', 'wikipedia')
            """
        ).fetchall()
        entity_to_person = {row["entity_id"]: row["person_id"] for row in rows}
        people = {row["id"]: row for row in db.execute("SELECT id, name, reign, category FROM person")}
        source_id = db.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
        existing = {
            (r[0], r[1], r[2], r[3])
            for r in db.execute("SELECT from_person_id, to_person_id, relation_type, reign FROM person_relation")
        }
    print(f"已匹配维基数据实体 {len(entity_to_person)} 个。", flush=True)

    # ---- 来源 A：维基数据亲属声明 ----
    entities = entity_data(sorted(entity_to_person))
    planned: list[tuple[str, str, str, str, str]] = []
    planned_pairs: set[tuple[str, str, str]] = set()
    existing_pairs = {(f, t, relation_type) for f, t, relation_type, _ in existing}

    def plan(owner: str, role: str, target: str) -> None:
        if role in ("sibling", "spouse") and owner > target:
            # 配偶与兄弟姐妹是对称关系：统一按 id 较小一方为起点，避免双向重复。
            owner, target = target, owner
        if role == "father":
            from_id, to_id, relation_type = target, owner, "父子"
        elif role == "mother":
            from_id, to_id, relation_type = target, owner, "母子"
        else:
            from_id, to_id = owner, target
            relation_type = {"spouse": "配偶", "child": "父子", "sibling": "兄弟姐妹"}[role]
        if (from_id, to_id, relation_type) in planned_pairs or (from_id, to_id, relation_type) in existing_pairs:
            return  # 同一配对只写一条，年号取子方（或声明方）所属时期
        planned_pairs.add((from_id, to_id, relation_type))
        if relation_type in ("父子", "母子"):
            reign = people[to_id]["reign"] or people[from_id]["reign"]
        else:
            reign = people[from_id]["reign"] or people[target]["reign"]
        planned.append((from_id, to_id, relation_type, reign, source_id))

    for entity_id, entity in entities.items():
        owner = entity_to_person.get(entity_id)
        if not owner:
            continue
        for property_id, (role, _) in KINSHIP_PROPERTIES.items():
            for value in entity_ids(entity, property_id):
                target = entity_to_person.get(value)
                if target and target != owner:
                    plan(owner, role, target)

    # ---- 来源 B：百度百科名片 ----
    baike_hits = 0
    if not args.skip_baike:
        # 官职名 -> 帝王不建家庭关系以外的条目；此处仅家庭类，不受君臣禁令影响。
        name_to_ids: dict[str, list[str]] = {}
        for person_id, row in people.items():
            name_to_ids.setdefault(row["name"], []).append(person_id)
        for person_id, row in people.items():
            if row["category"] not in ("皇帝", "后妃", "藩王", "名臣", "名将", "勋贵", "文人", "宦官"):
                continue
            card = baike_card(row["name"])
            if not card:
                time.sleep(0.25)
                continue
            baike_hits += 1
            for role, names in card.items():
                for value in names:
                    # 名片值可能带括注（如“马皇后（1332－1382）”），取括注前的人名。
                    base = value.split("（")[0].split("(")[0].strip()
                    candidates = name_to_ids.get(base, [])
                    if len(candidates) == 1 and candidates[0] != person_id:
                        plan(person_id, role, candidates[0])
            time.sleep(0.25)
        print(f"百度百科名片可用 {baike_hits} 位。", flush=True)

    print(f"拟写入关系 {len(planned)} 条。", flush=True)
    for row in planned[:12]:
        from_id, to_id, rel, reign, _ = row
        print(f"  {people[from_id]['name']} —{rel}— {people[to_id]['name']}（{reign}）")
    if args.dry_run:
        return 0

    with connect() as db:
        db.executemany(
            """
            INSERT OR IGNORE INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
            VALUES (?, ?, ?, ?, '', ?)
            """,
            planned,
        )
        total = db.execute("SELECT COUNT(*) FROM person_relation").fetchone()[0]
    print(f"写库完成，全库关系现 {total} 条。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
