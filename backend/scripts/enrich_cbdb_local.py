#!/usr/bin/env python3
"""用 CBDB 官方 SQLite 整库（本地）补全家族名录、关系边与仕历出身。

- CBDB 库：/tmp/cbdb_20260822.sqlite3（hf-mirror.com 下载，66 万人物）。
- 姓名匹配：库内繁体名经 t2s 与库内简体名比对；多候选取 index_year 最近者。
- 家族与子嗣：机器生成的栏目以 CBDB 亲属名录增强；人工校订栏目不动。
- 关系网：亲属映射到库内人物（唯一命中 + 同姓 + 生年校验）建家庭类边。
- 生平：偏薄者追加 CBDB 仕历、出身、籍贯与生卒行。
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from opencc import OpenCC  # noqa: E402

from app.database import connect, initialize_database  # noqa: E402

CBDB_PATH = Path(__file__).resolve().parents[1] / 'sources' / 'cbdb' / 'cbdb_20260822.sqlite3'
t2s = OpenCC("t2s")
s2t = OpenCC("s2t")

MACHINE_MARKS = ("以上为", "史料未见详载", "关系网络所载")
EDGE_RULES = (("父", "父子", "kin_to_self"), ("母", "母子", "kin_to_self"),
              ("子", "父子", "self_to_kin"), ("兄", "兄弟姐妹", None),
              ("弟", "兄弟姐妹", None), ("妻", "配偶", "self_to_kin"))


def kin_category(rel: str) -> str | None:
    rel = rel.strip()
    if rel.startswith("父"):
        return "父"
    if rel.startswith("母"):
        return "母"
    if rel.startswith("子"):
        return "子"
    if rel.startswith("女"):
        return "女"
    if rel.startswith(("兄", "弟", "姊", "妹")):
        return "兄弟姐妹"
    if rel.startswith("妻") or rel.startswith("配"):
        return "配偶"
    if rel.startswith("孫"):
        return "孙辈"
    if rel.startswith("祖"):
        return "祖辈"
    if rel.startswith("曾祖"):
        return "曾祖辈"
    if rel.startswith(("侄", "甥")):
        return "侄甥"
    return None


def main() -> int:
    initialize_database()
    cb = sqlite3.connect(f"file:{CBDB_PATH}?mode=ro", uri=True)
    cb.row_factory = sqlite3.Row

    with connect() as db:
        app = sqlite3.connect(":memory:")
        people = db.execute("SELECT id, name, years, category, reign FROM person ORDER BY id").fetchall()
        family_content = {r["person_id"]: r["content"] for r in db.execute("SELECT person_id, content FROM person_section WHERE section_key='family'")}
        life_content = {r["person_id"]: r["content"] for r in db.execute("SELECT person_id, content FROM person_section WHERE section_key='life'")}
        source_id = db.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
        existing_pairs = {(r[0], r[1], r[2]) for r in db.execute("SELECT from_person_id, to_person_id, relation_type FROM person_relation")}

    # 库名映射：CBDB 繁体名 t2s → 本库人物（简体）
    by_simplified: dict[str, list] = {}
    for person in people:
        by_simplified.setdefault(person["name"], []).append(person)

    resolved: dict[str, dict] = {}
    for person in people:
        cands = cb.execute(
            "SELECT c_personid, c_name_chn, c_index_year, c_birthyear, c_deathyear FROM BIOG_MAIN WHERE c_name_chn = ?",
            (s2t.convert(person["name"]),),
        ).fetchall()
        if not cands:
            continue
        m = re.match(r"^\s*(\d{4})", person["years"] or "")
        target_birth = int(m.group(1)) if m else None
        best = None
        for c in cands:
            iy = c["c_index_year"] or 0
            score = abs(iy - target_birth) if target_birth and iy else 9999
            if best is None or score < best[0]:
                best = (score, c)
        if best and best[0] <= 40:
            resolved[person["id"]] = best[1]
    print(f"CBDB 人物匹配 {len(resolved)}/748 位。", flush=True)

    family_enriched = 0
    life_enriched = 0
    edges: list[tuple[str, str, str, str, str]] = []
    planned: set[tuple[str, str, str]] = set(existing_pairs)

    with connect() as db:
        for person in people:
            person_id = person["id"]
            cbrow = resolved.get(person_id)
            if not cbrow:
                continue
            cb_id = cbrow["c_personid"]
            surname = person["name"][0]

            kinships = cb.execute(
                """
                SELECT k.c_kinrel_chn AS rel, b.c_name_chn AS kin_name, b.c_birthyear AS kin_birth
                FROM KIN_DATA kd
                JOIN KINSHIP_CODES k ON k.c_kincode = kd.c_kin_code
                JOIN BIOG_MAIN b ON b.c_personid = kd.c_kin_id
                WHERE kd.c_personid = ?
                """,
                (cb_id,),
            ).fetchall()

            # 1) 家族名录增强（机器生成的栏目）
            current_family = family_content.get(person_id, "")
            if any(mark in current_family for mark in MACHINE_MARKS):
                groups: dict[str, list[str]] = {}
                for k in kinships:
                    cat = kin_category(k["rel"])
                    name = t2s.convert(k["kin_name"] or "").strip()
                    if cat and name and name != person["name"]:
                        groups.setdefault(cat, []).append(name)
                if groups:
                    keep = [l for l in current_family.splitlines()
                            if l.startswith(("儿子：", "女儿：", "父亲：", "母亲：", "兄弟姐妹：", "配偶："))]
                    for cat, names in groups.items():
                        if cat in ("孙辈", "祖辈", "曾祖辈", "侄甥"):
                            continue
                        keep = [l for l in keep if not l.startswith(f"{cat}：") ] if cat != "兄弟姐妹" else keep
                    merged = list(dict.fromkeys(keep + [f"{cat}：{'、'.join(list(dict.fromkeys(names)))}。" for cat, names in groups.items() if cat not in ("孙辈", "祖辈", "曾祖辈", "侄甥")]))
                    content = "\n".join(merged) + "\n亲属名录据哈佛 CBDB 整库与公开资料；结局待逐条编核。"
                    db.execute("UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'family'", (content, person_id))
                    db.execute("UPDATE person SET family_summary = ? WHERE id = ?", (content, person_id))
                    family_enriched += 1

            # 2) 关系边
            def birth_of(pid: str):
                nums = re.findall(r"(1[3-7]\d{2})", next((p["years"] for p in people if p["id"] == pid), ""))
                return int(nums[0]) if nums else None

            def plan(from_id: str, to_id: str, relation_type: str):
                if from_id == to_id:
                    return
                cats = {p["category"] for p in people if p["id"] in (from_id, to_id)}
                if "帝王" in cats and cats & {"朝臣", "将帅", "文苑"}:
                    return
                if relation_type in ("配偶", "兄弟姐妹") and from_id > to_id:
                    from_id, to_id = to_id, from_id
                key = (from_id, to_id, relation_type)
                if key in planned:
                    return
                fb, cbb = birth_of(from_id), birth_of(to_id)
                if relation_type == "父子" and fb and cbb and not (15 <= cbb - fb <= 70):
                    return
                if relation_type == "母子" and fb and cbb and not (13 <= cbb - fb <= 55):
                    return
                if relation_type == "兄弟姐妹" and fb and cbb and abs(fb - cbb) > 20:
                    return
                planned.add(key)
                edges.append((from_id, to_id, relation_type, reign_by_id.get(to_id, "明代"), "", source_id))

            reign_by_id = {p["id"]: p["reign"] or "明代" for p in people}
            for k in kinships:
                cat = kin_category(k["rel"] or "")
                if cat not in ("父", "母", "子", "兄弟姐妹"):
                    continue
                kin_name = t2s.convert(k["kin_name"] or "").strip()
                candidates = by_simplified.get(kin_name, [])
                if len(candidates) != 1:
                    continue
                target = candidates[0]
                if target["name"][0] != surname and cat in ("父", "子", "兄弟姐妹"):
                    continue  # 家庭成员须同姓
                if cat == "父":
                    plan(target["id"], person_id, "父子")
                elif cat == "母":
                    plan(target["id"], person_id, "母子")
                else:
                    plan(person_id, target["id"], "父子" if cat == "子" else "兄弟姐妹")

            # 3) 生平追加仕历/出身/籍贯
            current_life = life_content.get(person_id, "")
            if len(current_life) < 1200:
                postings = cb.execute(
                    """
                    SELECT oc.c_office_chn AS office, po.c_firstyear AS fy
                    FROM POSTED_TO_OFFICE_DATA po JOIN OFFICE_CODES oc ON oc.c_office_id = po.c_office_id
                    WHERE po.c_personid = ? ORDER BY po.c_firstyear
                    """,
                    (cb_id,),
                ).fetchall()
                entries = cb.execute(
                    """
                    SELECT ec.c_entry_desc_chn AS kind, ed.c_year AS yr
                    FROM ENTRY_DATA ed JOIN ENTRY_CODES ec ON ec.c_entry_code = ed.c_entry_code
                    WHERE ed.c_personid = ? ORDER BY ed.c_year
                    """,
                    (cb_id,),
                ).fetchall()
                addr = cb.execute(
                    """
                    SELECT ac.c_name_chn AS addr FROM BIOG_ADDR_DATA ba
                    JOIN ADDR_CODES ac ON ac.c_addr_id = ba.c_addr_id
                    WHERE ba.c_personid = ? AND ba.c_addr_type = 1
                    """,
                    (cb_id,),
                ).fetchone()
                extra = []
                if addr:
                    extra.append(f"籍贯（据哈佛 CBDB）：{t2s.convert(addr['addr'])}。")
                offices = [f"{t2s.convert(r['office'])}（{r['fy'] or ''}）" for r in postings if r["office"]]
                if offices:
                    extra.append("仕历（据哈佛 CBDB）：" + "、".join(list(dict.fromkeys(offices))[:12]) + "。")
                kinds = [f"{t2s.convert(r['kind'])}（{r['yr'] or ''}）" for r in entries if r["kind"]]
                if kinds:
                    extra.append("出身（据哈佛 CBDB）：" + "、".join(list(dict.fromkeys(kinds))[:6]) + "。")
                if extra:
                    marker = "〔《明史》原文"
                    shi_block = ""
                    base = current_life
                    if marker in base:
                        shi_block = base[base.index(marker):].strip()
                        base = base[:base.index(marker)].strip()
                    content = (base + "\n\n" if base else "") + "\n".join(dict.fromkeys(extra))
                    if shi_block:
                        content += "\n\n" + shi_block
                    db.execute("UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'life'", (content, person_id))
                    life_enriched += 1

        db.executemany(
            """
            INSERT OR IGNORE INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(f, t, rt, reign_by_id.get(t, "明代"), note, source_id) for f, t, rt, reign, note, source_id in edges],
        )
        total = db.execute("SELECT COUNT(*) FROM person_relation").fetchone()[0]
        family_ok = db.execute(
            "SELECT COUNT(DISTINCT person_id) FROM person_section WHERE section_key='family' AND content NOT LIKE '%史料未见详载%'"
        ).fetchone()[0]
    print(f"CBDB 匹配 {len(resolved)} 位；家族增强 {family_enriched}；生平追加 {life_enriched}；新增关系 {len(edges)} 条（全库 {total}）。", flush=True)
    print(f"家族栏目有实料：{family_ok}/748。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
