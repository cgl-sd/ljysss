#!/usr/bin/env python3
"""在全卷《明史》原文上挖掘库内人物的亲属关系，补入 person_relation。

方法（从严）：
1. 传首定位：全卷按“某某，字/某”找传首；全名直配，单名（明史附传省姓）
   需其姓氏与本卷其他已配传主一致才采信。
2. 相邻两传之间为前一传主的传记（含附传）。在该段落内：
   - “子/弟/兄 + 名”紧邻称呼（允许“四子：辉祖、添福”冒号枚举）；
   - 后传起句含前传主全名 + “之子/之弟”标记。
3. 家庭成员须同姓（父子/兄弟），跨姓一律丢弃；帝王不与文臣武将建边。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import connect, initialize_database  # noqa: E402

BIO_HEAD_PATTERN = re.compile(r"^([\u4e00-\u9fa5·]{2,4})，", re.M)
HEAD_KINSHIP = re.compile(r"(之子|之弟|之兄|之孙|从子|从孙|弟也|兄也)")
PARENT_MARK = ("之子", "之孙")
SIBLING_MARK = ("之弟", "之兄", "弟也", "兄也")
NEAR_KINSHIP = re.compile(r"(子|弟|兄)[：:]?[长短三四五六七八九十]{0,2}([\u4e00-\u9fa5]{2,4})[，。：:、]")
ENUMERATION = re.compile(r"[二三四五六七八九十]?子[：:]([、\u4e00-\u9fa5]{2,60})")


def main() -> int:
    initialize_database()
    with connect() as db:
        people = db.execute("SELECT id, name, category, reign, years FROM person ORDER BY id").fetchall()
        source_id = db.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
        existing_pairs = {
            (r[0], r[1], r[2])
            for r in db.execute("SELECT from_person_id, to_person_id, relation_type FROM person_relation")
        }

    name_to_ids: dict[str, list] = {}
    given_to_ids: dict[str, list] = {}
    for person in people:
        name_to_ids.setdefault(person["name"], []).append(person)
        for given in (person["name"][1:], person["name"][2:]):
            if len(given) >= 2:
                given_to_ids.setdefault(given, []).append(person)
    category_by_id = {p["id"]: p["category"] for p in people}
    reign_by_id = {p["id"]: p["reign"] or "明代" for p in people}
    person_by_id = {p["id"]: p for p in people}

    corpus = Path(BACKEND_DIRECTORY) / "sources" / "mingshi"
    years_by_id = {p["id"]: p["years"] for p in people}
    planned: dict[tuple[str, str, str], str] = {}

    def plan(from_id: str, to_id: str, relation_type: str, note: str) -> None:
        if from_id == to_id:
            return
        # 生年合理性：父子差 15–70 年，兄弟差不超过 20 年；年份缺失时放行。
        def birth_of(pid: str):
            nums = re.findall(r"(1[3-7]\d{2})", years_by_id.get(pid, ""))
            return int(nums[0]) if nums else None
        if relation_type == "父子":
            fb, cb = birth_of(from_id), birth_of(to_id)
            if fb and cb and not (15 <= cb - fb <= 70):
                return
        if relation_type == "兄弟姐妹":
            fb, cb = birth_of(from_id), birth_of(to_id)
            if fb and cb and abs(fb - cb) > 20:
                return
        categories = {category_by_id.get(from_id), category_by_id.get(to_id)}
        if "帝王" in categories and categories & {"朝臣", "将帅", "文苑"}:
            return
        if relation_type in ("配偶", "兄弟姐妹") and from_id > to_id:
            from_id, to_id = to_id, from_id
        key = (from_id, to_id, relation_type)
        if key in planned or key in existing_pairs:
            return
        planned[key] = note

    for juan_file in sorted(corpus.glob("卷*.txt")):
        juan = int(juan_file.stem[1:])
        text = juan_file.read_text(encoding="utf-8")
        heads: list[tuple[str, int]] = [(m.group(1), m.start()) for m in BIO_HEAD_PATTERN.finditer(text)]
        resolved: list[tuple[object, int]] = []
        for head_name, pos in heads:
            for person in name_to_ids.get(head_name, []):
                resolved.append((person, pos))
        surnames_in_juan = {p["name"][0] for p, _ in resolved}
        for head_name, pos in heads:
            if any(p["name"] == head_name for p, _ in resolved):
                continue
            candidates = [p for p in given_to_ids.get(head_name, []) if p["name"][0] in surnames_in_juan]
            if len(candidates) == 1:
                resolved.append((candidates[0], pos))
        resolved.sort(key=lambda item: item[1])
        if len(resolved) < 2:
            continue

        def segment_of(index: int) -> str:
            start = resolved[index][1]
            end = resolved[index + 1][1] if index + 1 < len(resolved) else len(text)
            return text[start:end]

        def resolve_token(token: str, surname: str):
            candidates = name_to_ids.get(token, [])
            if len(candidates) == 1:
                return candidates[0]
            given_candidates = [p for p in given_to_ids.get(token, []) if p["name"][0] == surname]
            if len(given_candidates) == 1:
                return given_candidates[0]
            return None

        for index in range(len(resolved)):
            a, pos = resolved[index]
            segment = segment_of(index)
            surname = a["name"][0]
            if index + 1 < len(resolved):
                b, b_pos = resolved[index + 1]
                newline = text.find("\n", b_pos)
                head_line = text[b_pos:newline if newline > 0 else b_pos + 60][:60]
                if a["name"] in head_line and HEAD_KINSHIP.search(head_line):
                    if any(mark in head_line for mark in PARENT_MARK):
                        plan(a["id"], b["id"], "父子", f"《明史》卷{juan}附传体例")
                    elif any(mark in head_line for mark in SIBLING_MARK):
                        plan(a["id"], b["id"], "兄弟姐妹", f"《明史》卷{juan}附传体例")
            for match in NEAR_KINSHIP.finditer(segment):
                target = resolve_token(match.group(2), surname)
                if not target or target["name"][0] != surname:
                    continue
                note = f"《明史》卷{juan}“{match.group(0).rstrip('，。：:、')}”"
                if match.group(1) == "子":
                    plan(a["id"], target["id"], "父子", note)
                elif match.group(1) in ("弟", "兄"):
                    plan(a["id"], target["id"], "兄弟姐妹", note)
            for match in ENUMERATION.finditer(segment):
                for token in match.group(1).split("、"):
                    target = resolve_token(token, surname)
                    if target and target["name"][0] == surname:
                        plan(a["id"], target["id"], "父子", f"《明史》卷{juan}子嗣名录")

    # 家族栏目增强：从各人传段挖 父X / 娶某氏 / 妻某氏 信号，替换诚实占位。
    mined_family: dict[str, list[str]] = {}
    for juan_file2 in sorted(corpus.glob("卷*.txt")):
        juan2 = int(juan_file2.stem[1:])
        text2 = juan_file2.read_text(encoding="utf-8")
        heads2: list[tuple[str, int]] = [(m.group(1), m.start()) for m in BIO_HEAD_PATTERN.finditer(text2)]
        resolved2: list[tuple[object, int]] = []
        for head_name, pos in heads2:
            for person in name_to_ids.get(head_name, []):
                resolved2.append((person, pos))
        surnames2 = {p["name"][0] for p, _ in resolved2}
        for head_name, pos in heads2:
            if any(p["name"] == head_name for p, _ in resolved2):
                continue
            candidates = [p for p in given_to_ids.get(head_name, []) if p["name"][0] in surnames2]
            if len(candidates) == 1:
                resolved2.append((candidates[0], pos))
        resolved2.sort(key=lambda item: item[1])
        for index in range(len(resolved2)):
            a, pos = resolved2[index]
            end = resolved2[index + 1][1] if index + 1 < len(resolved2) else len(text2)
            seg = text2[pos:end]
            surname = a["name"][0]
            lines = []
            for m in re.finditer(r"父([\u4e00-\u9fa5]{2,4})[，。]", seg):
                if m.group(1)[0] == surname and m.group(1) != a["name"]:
                    lines.append(f"父亲：{m.group(1)}（《明史》卷{juan2}）。")
            for m in re.finditer(r"(?:娶|妻)([\u4e00-\u9fa5]{1,2})氏", seg):
                lines.append(f"配偶：{m.group(1)}氏（《明史》卷{juan2}）。")
            if lines:
                mined_family.setdefault(a["id"], []).extend(dict.fromkeys(lines))

    rows = [
        (from_id, to_id, relation_type, reign_by_id.get(to_id, "明代"), note, source_id)
        for (from_id, to_id, relation_type), note in planned.items()
    ]
    with connect() as db:
        db.executemany(
            """
            INSERT OR IGNORE INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        total = db.execute("SELECT COUNT(*) FROM person_relation").fetchone()[0]
        family_enriched = 0
        for person_id, lines in mined_family.items():
            row = db.execute(
                """
                SELECT 1 FROM person_section
                WHERE person_id = ? AND section_key = 'family' AND content LIKE '%史料未见详载%'
                """,
                (person_id,),
            ).fetchone()
            if not row:
                continue
            content = "\n".join(dict.fromkeys(lines)) + "\n以上自《明史》传文检出；其余亲属未详。"
            db.execute(
                """
                UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'family'
                """,
                (content, person_id),
            )
            db.execute("UPDATE person SET family_summary = ? WHERE id = ?", (content, person_id))
            family_enriched += 1
    print(f"《明史》挖掘新增关系 {len(rows)} 条，全库现 {total} 条；家族栏目增强 {family_enriched} 位。", flush=True)
    for row in rows[:20]:
        print(f"  {person_by_id[row[0]]['name']} —{row[2]}— {person_by_id[row[1]]['name']} | {row[4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
