#!/usr/bin/env python3
"""从编辑库投影出阅读端发布库。

编辑库（backend/data/ming_history.sqlite3）同时服务内容编辑流水线，包含
维基原文、CBDB、明史语料等 App 不读取的表。发布库只保留阅读端实际查询的
表及其索引与触发器，随 APK 打包，减小安装体积。

用法：build_release_database.py <编辑库路径> <发布库路径>
"""
import sqlite3
import sys
import os
import re

# 阅读端 BundledMingRepository 读取的全部表；person_category 因 person 表
# 的登记触发器引用而一并保留。
RELEASE_TABLES = {
    "person",
    "person_category",
    "person_section",
    "person_relation",
    "event",
    "event_section",
    "event_participant",
    "reign",
    "source",
    "institution",
    "institution_section",
    "institution_person",
    "institution_promotion",
    "institution_reform",
    "special_item",
    "special_section",
    "special_person",
    "travel_guide",
    "travel_guide_section",
}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_release_database.py <src.sqlite3> <dst.sqlite3>")
    src_path, dst_path = sys.argv[1], sys.argv[2]
    if os.path.exists(dst_path):
        os.remove(dst_path)
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)

    dst = sqlite3.connect(dst_path)
    try:
        dst.execute("PRAGMA foreign_keys = OFF")
        dst.execute("ATTACH DATABASE ? AS src", (f"file:{src_path}?mode=ro",))
        objects = dst.execute(
            "SELECT type, name, tbl_name, sql FROM src.sqlite_master "
            "WHERE sql IS NOT NULL ORDER BY rowid"
        ).fetchall()

        kept = set()
        for kind, name, tbl_name, sql in objects:
            if kind == "table":
                if name in RELEASE_TABLES:
                    dst.execute(sql)
                    kept.add(name)
            elif kind in ("index", "trigger"):
                if tbl_name not in RELEASE_TABLES:
                    continue
                referenced = set(re.findall(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-z_]+)", sql, re.I))
                if referenced - RELEASE_TABLES:
                    # 编辑端校验触发器引用已裁剪表（如 person_section_definition），阅读端不需要。
                    continue
                dst.execute(sql)
            # views 不属于阅读端数据，跳过

        missing = RELEASE_TABLES - kept
        if missing:
            raise SystemExit(f"release tables missing from source: {sorted(missing)}")

        # person 的登记触发器依赖 person_category，先填被引用表。
        for table in sorted(kept, key=lambda t: (t not in {"person_category", "source"}, t)):
            dst.execute(f"INSERT INTO {table} SELECT * FROM src.{table}")
        dst.commit()

        if dst.execute("PRAGMA foreign_key_check").fetchall():
            raise SystemExit("foreign key violations in release database")
        dst.execute("PRAGMA journal_mode = DELETE")
        dst.execute("VACUUM")
        dst.commit()
    finally:
        dst.close()


if __name__ == "__main__":
    main()
