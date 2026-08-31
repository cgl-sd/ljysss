#!/usr/bin/env python3
"""发布前校验机构与典章正文、关联和逐条资源。"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "backend" / "data" / "content"
RESOURCES = ROOT / "app" / "src" / "main" / "res" / "drawable-nodpi"
BAD_TEXT = re.compile(r"[A-Za-z]|旅游|景区|博物馆|世界文化遗产|文物保护单位|非物质文化遗产|外文|英文|拉丁|转写|现为|管理中心")


def rows(table: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    institutions = rows("institution")
    institution_sections = rows("institution_section")
    specials = rows("special_item")
    special_sections = rows("special_section")
    errors: list[str] = []
    for table, records, key in (("institution_section", institution_sections, "institution_id"), ("special_section", special_sections, "special_item_id")):
        grouped: dict[str, list[dict]] = defaultdict(list)
        for record in records:
            grouped[record[key]].append(record)
            if len(record.get("content", "").strip()) < 50:
                errors.append(f"{table}:{record[key]}正文过短")
            if BAD_TEXT.search(record.get("content", "")):
                errors.append(f"{table}:{record[key]}含禁用文字")
        for item_id, group in grouped.items():
            if len(group) != 4 or len({record["content"] for record in group}) != 4:
                errors.append(f"{table}:{item_id}分栏不完整或重复")
    for table, records, key in (("institution", institutions, "id"), ("special_item", specials, "id")):
        assets = [record.get("image_asset", "") for record in records]
        if len(assets) != len(set(assets)):
            errors.append(f"{table}存在重复图片资源")
        for record in records:
            if not record.get("image_asset") or not (RESOURCES / f"{record['image_asset']}.xml").is_file():
                errors.append(f"{table}:{record[key]}缺少专属图片")
            value = " ".join(str(record.get(field, "")) for field in ("name", "function", "description"))
            if BAD_TEXT.search(value):
                errors.append(f"{table}:{record[key]}摘要含禁用文字")
    database = ROOT / "backend" / "data" / "ming_history.sqlite3"
    with sqlite3.connect(database) as connection:
        expected = {"institution": len(institutions), "institution_section": len(institution_sections), "special_item": len(specials), "special_section": len(special_sections)}
        for table, count in expected.items():
            actual = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if actual != count:
                errors.append(f"SQLite {table}={actual}，JSONL={count}")
    if errors:
        for error in errors:
            print("错误：" + error)
        return 1
    print(f"校验通过：机构 {len(institutions)} 条、典章 {len(specials)} 条、专属图片 {len(institutions) + len(specials)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
