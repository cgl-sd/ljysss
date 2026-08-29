#!/usr/bin/env python3
"""Complete the local reading schema for records awaiting external verification.

This is intentionally conservative: it creates the same display sections as a
researched record, but never invents education, office, family, or event facts
where the imported index does not establish them.  Those entries remain marked
``未校验`` until a precise encyclopedia or document match is recorded.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import connect, initialize_database  # noqa: E402

PENDING_FAMILY = "相关家族与子嗣资料尚待核验。"


def unverified_life(name: str, years: str) -> str:
    return (
        f"{name}已纳入本项目的明代人物档案。现有基础索引记录的生卒区间为“{years}”。"
        "在尚未取得可与具体个人精确对应的百科或文献条目前，本条不据此推断其教育经历、"
        "仕历、封号、事迹或家族关系；这些信息将在逐项核验后补入。"
    )


def add_person_templates(db: sqlite3.Connection) -> int:
    people = db.execute(
        """
        SELECT id, name, years FROM person
        WHERE source_id = 'cbdb-20210525'
          AND NOT EXISTS (
              SELECT 1 FROM person_section
              WHERE person_id = person.id AND section_key = 'life'
          )
        ORDER BY id
        """
    ).fetchall()
    for person in people:
        life = unverified_life(person["name"], person["years"])
        db.execute(
            "UPDATE person SET biography = ?, family_summary = ?, verification_status = '未校验' WHERE id = ?",
            (life, PENDING_FAMILY, person["id"]),
        )
        db.executemany(
            """
            INSERT INTO person_section(person_id, section_key, title, position, content)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(person_id, section_key) DO UPDATE SET
                title = excluded.title, position = excluded.position, content = excluded.content
            """,
            [
                (person["id"], "life", "生平（含教育背景）", 1, life),
                (person["id"], "family", "家族与子嗣", 2, PENDING_FAMILY),
            ],
        )
    return len(people)


def synchronize_unverified_family_fields(db: sqlite3.Connection) -> int:
    """Keep the API-facing field and the display section identical for unresolved records."""

    result = db.execute(
        """
        UPDATE person
        SET family_summary = ?
        WHERE source_id = 'cbdb-20210525'
          AND verification_status = '未校验'
          AND family_summary = ''
        """,
        (PENDING_FAMILY,),
    )
    db.execute(
        """
        UPDATE person_section
        SET content = ?
        WHERE section_key = 'family'
          AND person_id IN (
              SELECT id FROM person
              WHERE source_id = 'cbdb-20210525'
                AND verification_status = '未校验'
                AND family_summary = ?
          )
        """,
        (PENDING_FAMILY, PENDING_FAMILY),
    )
    return result.rowcount


def add_event_templates(db: sqlite3.Connection) -> int:
    events = db.execute(
        """
        SELECT id, year, month, title, summary, detail, participants, consequence
        FROM event
        WHERE NOT EXISTS (
            SELECT 1 FROM event_section
            WHERE event_id = event.id AND section_key = 'background'
        )
        ORDER BY year, id
        """
    ).fetchall()
    for event in events:
        background = f"{event['year']}年{event['month']}，{event['summary']}"
        people = event["participants"] or "相关参与者资料将在后续人物关联页补充。"
        impact = event["consequence"] or event["summary"]
        db.executemany(
            """
            INSERT INTO event_section(event_id, section_key, title, position, content)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(event_id, section_key) DO UPDATE SET
                title = excluded.title, position = excluded.position, content = excluded.content
            """,
            [
                (event["id"], "background", "背景", 1, background),
                (event["id"], "course", "经过", 2, event["detail"]),
                (event["id"], "people", "相关人物", 3, people),
                (event["id"], "result", "结果", 4, event["consequence"]),
                (event["id"], "impact", "影响", 5, impact),
                (event["id"], "verification", "资料状态", 6, "未校验"),
            ],
        )
    return len(events)


def main() -> int:
    initialize_database()
    with connect() as db:
        people = add_person_templates(db)
        synchronized = synchronize_unverified_family_fields(db)
        events = add_event_templates(db)
    print(f"已建立：{people} 个人物档案模板，{events} 个事件档案模板；同步 {synchronized} 条待核验家族资料。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
