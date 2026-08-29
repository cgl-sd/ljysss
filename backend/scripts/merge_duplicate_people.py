#!/usr/bin/env python3
"""合并简繁重复人物行：维基收录侧（wiki- 前缀、繁体名）并入精选库侧（稳定 id）。

保留精选 id（边、明史传文、CBDB 映射均引用它），若维基侧行内容更丰富则
移植其生平/家族/维基全文/校验状态；维基侧的关系边重映射到保留 id 后按
(起点, 终点, 类型) 去重；随后删除维基侧行及其引用。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
t2s = OpenCC("t2s")


def main() -> int:
    app = sqlite3.connect(BACKEND / "data" / "ming_history.sqlite3")
    app.row_factory = sqlite3.Row

    rows = app.execute("SELECT id, name, biography FROM person").fetchall()
    by_simplified: dict[str, list] = {}
    for r in rows:
        by_simplified.setdefault(t2s.convert(r["name"]), []).append(r)

    merged = removed = 0
    for key, group in by_simplified.items():
        if len(group) < 2:
            continue
        curated = [r for r in group if not r["id"].startswith("wiki-")]
        keep = curated[0] if curated else max(group, key=lambda r: len(r["biography"] or ""))
        keep_id = keep["id"]
        for donor in group:
            if donor["id"] == keep_id:
                continue
            donor_id = donor["id"]
            # 内容移植：维基侧更丰富则采用
            if len(donor["biography"] or "") > len(keep["biography"] or ""):
                app.execute("UPDATE person SET biography = ? WHERE id = ?", (donor["biography"], keep_id))
            dl = app.execute("SELECT content FROM person_section WHERE person_id=? AND section_key='life'", (donor_id,)).fetchone()
            kl = app.execute("SELECT content FROM person_section WHERE person_id=? AND section_key='life'", (keep_id,)).fetchone()
            if dl and (not kl or len(dl["content"]) > len(kl["content"])):
                app.execute(
                    "INSERT INTO person_section(person_id, section_key, title, position, content) VALUES (?, 'life', '生平', 0, ?) "
                    "ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content",
                    (keep_id, dl["content"]),
                )
            df = app.execute("SELECT content FROM person_section WHERE person_id=? AND section_key='family'", (donor_id,)).fetchone()
            kf = app.execute("SELECT content FROM person_section WHERE person_id=? AND section_key='family'", (keep_id,)).fetchone()
            if df and (not kf or len(df["content"]) > len(kf["content"])):
                app.execute(
                    "INSERT INTO person_section(person_id, section_key, title, position, content) VALUES (?, 'family', '家族', 1, ?) "
                    "ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content",
                    (keep_id, df["content"]),
                )
            app.execute(
                """
                INSERT INTO person_wiki(person_id, wiki_title, full_text)
                SELECT ?, wiki_title, full_text FROM person_wiki WHERE person_id = ?
                ON CONFLICT(person_id) DO UPDATE SET wiki_title = excluded.wiki_title, full_text = excluded.full_text
                """,
                (keep_id, donor_id),
            )
            # 关系边重映射
            for e in app.execute(
                "SELECT from_person_id, to_person_id, relation_type, reign, note, source_id FROM person_relation "
                "WHERE from_person_id = ? OR to_person_id = ?",
                (donor_id, donor_id),
            ).fetchall():
                f = keep_id if e["from_person_id"] == donor_id else e["from_person_id"]
                t = keep_id if e["to_person_id"] == donor_id else e["to_person_id"]
                if f == t:
                    continue
                app.execute(
                    """
                    INSERT OR IGNORE INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (f, t, e["relation_type"], e["reign"], e["note"], e["source_id"]),
                )
            # 删除维基侧重复行及其引用
            app.execute("DELETE FROM person_relation WHERE from_person_id = ? OR to_person_id = ?", (donor_id, donor_id))
            app.execute("DELETE FROM content_reference WHERE content_type='person' AND content_id = ?", (donor_id,))
            app.execute("DELETE FROM person_section WHERE person_id = ?", (donor_id,))
            app.execute("DELETE FROM person_wiki WHERE person_id = ?", (donor_id,))
            app.execute("DELETE FROM person_cbdb WHERE person_id = ?", (donor_id,))
            app.execute("DELETE FROM person_mingshi WHERE person_id = ?", (donor_id,))
            app.execute("DELETE FROM person WHERE id = ?", (donor_id,))
            merged += 1
            removed += 1

    app.commit()
    total = app.execute("SELECT COUNT(*) FROM person").fetchone()[0]
    print(f"合并重复人物 {merged} 组（删除 {removed} 行），全库现 {total} 人。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
