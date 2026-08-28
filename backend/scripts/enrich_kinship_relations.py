#!/usr/bin/env python3
"""把维基数据亲属声明结构化写入 person_relation，补全人物关系网络。

数据来源：已完成身份匹配的人物实体（person_research 中 provider 为
wikidata / wikipedia 且 status = matched）的 P22 父亲、P25 母亲、
P26 配偶、P40 子女、P3373 兄弟姐妹声明。

写入规则：
- 仅当亲属对象同样是库内人物（能通过实体 id 反查 person.id）才建关系；
  库外亲属仍保留在各人“家族与子嗣”栏目文字里。
- 关系类型：父子 / 母子 / 配偶 / 兄弟姐妹，与 App 端 RelationshipType
  标签一一对应；兄弟姐妹只按 id 较小的一方写入，避免双向重复。
- 皇帝的宗室家庭关系允许建立；皇帝与文臣武将的臣属关系仍被禁止。
- INSERT OR IGNORE：不覆盖人工编目的既有关系。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser(description="结构化补录维基数据亲属关系")
    parser.add_argument("--dry-run", action="store_true", help="只打印将写入的关系，不写库")
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
        people = {row["id"]: row for row in db.execute("SELECT id, name, reign FROM person")}
        source_id = db.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
        existing = {
            (r[0], r[1], r[2], r[3])
            for r in db.execute("SELECT from_person_id, to_person_id, relation_type, reign FROM person_relation")
        }
    print(f"已匹配实体 {len(entity_to_person)} 个。", flush=True)

    entities = entity_data(sorted(entity_to_person))
    planned: list[tuple[str, str, str, str, str]] = []
    for entity_id, entity in entities.items():
        owner = entity_to_person.get(entity_id)
        if not owner:
            continue
        for property_id, (role, relation_type) in KINSHIP_PROPERTIES.items():
            for value in entity_ids(entity, property_id):
                target = entity_to_person.get(value)
                if not target or target == owner:
                    continue
                if role == "sibling" and owner > target:
                    continue  # 兄弟姐妹只写一个方向
                if role == "father":
                    from_id, to_id = target, owner
                elif role == "mother":
                    from_id, to_id = target, owner
                else:
                    from_id, to_id = owner, target
                reign = people[owner]["reign"] or people[target]["reign"]
                key = (from_id, to_id, relation_type, reign)
                if key in existing:
                    continue
                existing.add(key)
                planned.append((*key, source_id))

    print(f"拟写入关系 {len(planned)} 条。", flush=True)
    for row in planned[:10]:
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
    time.sleep(0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
