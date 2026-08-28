#!/usr/bin/env python3
"""Import a reproducible, provenance-preserving Ming index from CBDB SQLite.

The script intentionally imports only basic biographical index fields.  It does
not infer offices, kinship, portraits, or a narrative biography from unreviewed
notes.  The source database remains outside this repository.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.catalog import CBDB_SOURCE  # noqa: E402
from app.database import connect, initialize_database  # noqa: E402

MING_DYNASTY_ID = 19


def normalized_name(value: str | None) -> str:
    return "".join((value or "").split())


def display_years(birth_year: int | None, death_year: int | None) -> str:
    birth = birth_year if birth_year and 1000 <= birth_year <= 1800 else None
    death = death_year if death_year and 1000 <= death_year <= 1800 else None
    if birth and death:
        return f"{birth}—{death}"
    if birth:
        return f"{birth}—？"
    if death:
        return f"？—{death}"
    return "生卒未详"


def index_summary(index_year: int | None) -> str:
    if index_year and 1000 <= index_year <= 1800:
        return f"CBDB 收录的明代人物，索引年代为 {index_year} 年。"
    return "CBDB 收录的明代人物，生平索引待进一步校核。"


def source_rows(source_path: Path, limit: int, existing_names: set[str]) -> list[dict[str, object]]:
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in source.execute("PRAGMA table_info(BIOG_MAIN)")}
        required = {"c_personid", "c_name_chn", "c_index_year", "c_birthyear", "c_deathyear", "c_dy"}
        if not required.issubset(columns):
            missing = ", ".join(sorted(required - columns))
            raise ValueError(f"CBDB BIOG_MAIN 缺少字段：{missing}")

        selected: list[dict[str, object]] = []
        seen_names = set(existing_names)
        cursor = source.execute(
            """
            SELECT c_personid, c_name_chn, c_index_year, c_birthyear, c_deathyear
            FROM BIOG_MAIN
            WHERE c_dy = ? AND TRIM(COALESCE(c_name_chn, '')) <> ''
            ORDER BY
                CASE WHEN c_birthyear BETWEEN 1000 AND 1800 THEN 0 ELSE 1 END,
                CASE WHEN c_index_year BETWEEN 1000 AND 1800 THEN c_index_year ELSE 9999 END,
                c_personid
            """,
            (MING_DYNASTY_ID,),
        )
        for row in cursor:
            name = normalized_name(row["c_name_chn"])
            if name in seen_names:
                continue
            seen_names.add(name)
            years = display_years(row["c_birthyear"], row["c_deathyear"])
            summary = index_summary(row["c_index_year"])
            selected.append(
                {
                    "id": f"cbdb-{row['c_personid']}",
                    "name": name,
                    "title": "CBDB 明代人物（待校核）",
                    "reign": "明代",
                    "years": years,
                    "category": "相关人物",
                    "courtesy_name": "",
                    "summary": summary,
                    "biography": (
                        f"{summary} 本项目目前仅保留姓名与年代索引；具体仕历、亲属、封号和长篇生平"
                        "须按原始资料逐条校核后补录。"
                    ),
                    "source_id": CBDB_SOURCE["id"],
                }
            )
            if len(selected) == limit:
                return selected
        return selected
    finally:
        source.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="导入 CBDB 明代人物基础索引")
    parser.add_argument("--source", type=Path, required=True, help="CBDB SQLite 数据库路径")
    parser.add_argument("--limit", type=int, default=1200, help="最多导入多少条唯一中文姓名记录（默认 1200）")
    parser.add_argument("--replace", action="store_true", help="替换本项目已有的 cbdb-* 导入记录")
    args = parser.parse_args()
    if args.limit < 1000:
        parser.error("--limit 必须不少于 1000，才能满足人物目录的首批规模")
    if not args.source.is_file():
        parser.error(f"找不到 CBDB 数据库：{args.source}")

    initialize_database()
    with connect() as destination:
        existing_names = {
            normalized_name(row[0])
            for row in destination.execute(
                "SELECT name FROM person WHERE source_id <> ?", (CBDB_SOURCE["id"],)
            )
        }
    rows = source_rows(args.source, args.limit, existing_names)
    if len(rows) < 1000:
        raise RuntimeError(f"仅找到 {len(rows)} 条可导入的唯一明代人物，未达到 1000 条")

    with connect() as destination:
        present = destination.execute("SELECT COUNT(*) FROM person WHERE id GLOB 'cbdb-*'").fetchone()[0]
        if present and not args.replace:
            raise RuntimeError("已有 CBDB 导入记录；如确认替换，请显式加 --replace")
        if args.replace:
            destination.execute("DELETE FROM person WHERE id GLOB 'cbdb-*'")
        destination.executemany(
            """
            INSERT INTO person(id, name, title, reign, years, category, courtesy_name, summary, biography, source_id)
            VALUES (:id, :name, :title, :reign, :years, :category, :courtesy_name, :summary, :biography, :source_id)
            """,
            rows,
        )
    print(f"已导入 {len(rows)} 条 CBDB 明代人物索引（来源：{CBDB_SOURCE['id']}）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
