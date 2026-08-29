#!/usr/bin/env python3
"""CBDB（哈佛中国历代人物传记资料库）结构化补全。

- 按姓名解析 CBDB 人物 id，取全量 JSON（亲属、仕历、出身、生卒籍贯）。
- 身份闸门：生卒年与库内年份须相近（±45 年），或朝代为明；不符者丢弃。
- 家族与子嗣：机器生成的栏目（含“以上为/史料未见详载”标记）以 CBDB 亲属
  名录增强；56 位核心人物的人工校订栏目不动。
- 关系网：亲属中能在库内唯一命中的人物（简繁转换后）建家庭类边。
- 生平：无维基全文的偏薄生平，追加 CBDB 仕历、出身与生卒籍贯行。
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from opencc import OpenCC  # noqa: E402

from app.database import connect, initialize_database  # noqa: E402

API = "https://cbdb.fas.harvard.edu/cbdbapi/person.php"
UA = "LiangjingResearch/1.0 (educational)"
s2t = OpenCC("s2t")
t2s = OpenCC("t2s")

MACHINE_MARKS = ("以上为", "史料未见详载", "关系网络所载")
ROSTER_ORDER = ["父", "母", "妻", "子", "女", "兄", "弟", "祖父", "曾祖", "孙"]

# 边映射：KinRelName → (关系类型, 方向 self→kin 或 kin→self)
EDGE_RULES = (
    ("父", "父子", "kin_to_self"),
    ("母", "母子", "kin_to_self"),
    ("子", "父子", "self_to_kin"),
    ("兄", "兄弟姐妹", None),
    ("弟", "兄弟姐妹", None),
    ("妻", "配偶", "self_to_kin"),
)


def http_json(url: str) -> dict:
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=40) as resp:
        return json.load(resp)


def as_list(node) -> list:
    if node is None:
        return []
    return node if isinstance(node, list) else [node]


def parse_years(text: str) -> tuple[int | None, int | None]:
    match = re.match(r"^\s*([?？\d]{1,4})\s*—\s*([?？\d]{1,4})\s*$", text or "")
    if match:
        return (
            int(match.group(1)) if match.group(1).isdigit() else None,
            int(match.group(2)) if match.group(2).isdigit() else None,
        )
    years = re.findall(r"(1[3-7]\d{2})", text)
    return (int(years[0]) if years else None, int(years[1]) if len(years) > 1 else None)


def resolve_id(name: str) -> str | None:
    html = urlopen(
        Request(f"{API}?name={quote(name)}", headers={"User-Agent": UA}), timeout=30
    ).read().decode("utf-8", "ignore")
    ids = re.findall(r"人物資料庫 - (\d+)", html)
    return ids[0] if ids else None


def identity_ok(person, basic: dict) -> bool:
    dynasty = basic.get("DynastyBirth", "")
    index_year = basic.get("IndexYear") or basic.get("YearBirth")
    expected_birth, expected_death = parse_years(person["years"])
    if index_year and str(index_year).isdigit():
        year = int(index_year)
        if expected_birth and abs(year - expected_birth) <= 45:
            return True
        if expected_death and 0 <= expected_death - year <= 90:
            return True
        if not expected_birth and not expected_death and dynasty == "明":
            return True
        return False
    return dynasty == "明"


def roster_lines(kinships: list[dict]) -> list[str]:
    """按 CBDB 关系称谓归组，产出家族名录行（繁体转简体）。"""
    groups: dict[str, list[str]] = {}
    for k in kinships:
        rel = (k.get("KinRelName") or "").strip()
        name = t2s.convert(k.get("KinPersonName") or "")
        name = re.sub(r"[（(].*?[)）]", "", name).strip()
        if not rel or not name:
            continue
        groups.setdefault(rel, []).append(name)
    ordered = {}
    for key in ROSTER_ORDER:
        for rel, names in groups.items():
            if rel.startswith(key) and rel not in ordered:
                ordered[rel] = names
    for rel, names in groups.items():
        ordered.setdefault(rel, names)
    lines = []
    for rel, names in ordered.items():
        seen = list(dict.fromkeys(names))
        lines.append(f"{rel}：{'、'.join(seen)}。")
    return lines


def office_lines(postings: list[dict]) -> list[str]:
    rows = []
    for p in postings:
        office = t2s.convert(p.get("OfficeName") or "")
        year = p.get("FirstYear") or ""
        if office:
            rows.append(f"{office}（{year}）" if year else office)
    if not rows:
        return []
    return ["仕历（据哈佛 CBDB）：" + "、".join(dict.fromkeys(rows[:12])) + "。"]


def entry_lines(entries: list[dict]) -> list[str]:
    kinds = []
    for e in entries:
        kind = t2s.convert(e.get("EntryTypeName-Chinese") or "")
        year = e.get("EntryYear") or ""
        if kind:
            kinds.append(f"{kind}（{year}）" if year else kind)
    if not kinds:
        return []
    return ["出身（据哈佛 CBDB）：" + "、".join(dict.fromkeys(kinds[:6])) + "。"]


def main() -> int:
    initialize_database()
    with connect() as db:
        people = db.execute("SELECT id, name, years, category, reign FROM person ORDER BY id").fetchall()
        family_content = {
            row["person_id"]: row["content"]
            for row in db.execute("SELECT person_id, content FROM person_section WHERE section_key = 'family'")
        }
        life_content = {
            row["person_id"]: row["content"]
            for row in db.execute("SELECT person_id, content FROM person_section WHERE section_key = 'life'")
        }
        source_id = db.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
        existing_pairs = {
            (r[0], r[1], r[2])
            for r in db.execute("SELECT from_person_id, to_person_id, relation_type FROM person_relation")
        }
        name_to_ids: dict[str, list] = {}
        for person in people:
            name_to_ids.setdefault(person["name"], []).append(person)
        person_names = {p["id"]: p["name"] for p in people}
        reign_by_id = {p["id"]: p["reign"] or "明代" for p in people}

    family_enriched = 0
    edges: list[tuple[str, str, str, str, str]] = []
    life_enriched = 0
    resolved = 0
    for person in people:
        person_id = person["id"]
        try:
            cbdb_id = resolve_id(person["name"])
            if not cbdb_id:
                time.sleep(0.2)
                continue
            detail = http_json(f"{API}?id={cbdb_id}&o=json")
        except Exception as error:
            print(f"{person['name']}: CBDB 查询失败（{error}）", flush=True)
            time.sleep(1)
            continue
        try:
            person_node = detail["Package"]["PersonAuthority"]["PersonInfo"]["Person"]
            if isinstance(person_node, list):
                person_node = person_node[0]
            basic = person_node.get("BasicInfo", {})
            if not identity_ok(person, basic):
                time.sleep(0.3)
                continue
            resolved += 1
            kinships = as_list(person_node.get("PersonKinshipInfo", {}).get("Kinship"))
            postings = as_list(person_node.get("PersonPostings", {}).get("Posting"))
            entries = as_list(person_node.get("PersonEntryInfo", {}).get("Entry"))
        except Exception as error:
            print(f"{person['name']}: 解析失败（{error}）", flush=True)
            time.sleep(0.3)
            continue

        with connect() as db:
            # 1) 家族名录增强（机器生成的栏目；人工校订不动）
            current_family = family_content.get(person_id, "")
            is_machine = any(mark in current_family for mark in MACHINE_MARKS)
            if is_machine:
                lines = roster_lines(kinships)
                if lines:
                    keep = [l for l in current_family.splitlines() if l.startswith(("儿子：", "女儿：", "父亲：", "母亲：", "兄弟姐妹：", "配偶："))]
                    merged = list(dict.fromkeys(keep + lines))
                    content = "\n".join(merged) + "\n亲属名录据哈佛 CBDB 与公开资料；结局待逐条编核。"
                    db.execute(
                        "UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'family'",
                        (content, person_id),
                    )
                    db.execute("UPDATE person SET family_summary = ? WHERE id = ?", (content, person_id))
                    family_enriched += 1

            # 2) 关系边：CBDB 亲属映射到库内人物（唯一命中 + 生年校验）
            def birth_of(pid: str):
                nums = re.findall(r"(1[3-7]\d{2})", next((p["years"] for p in people if p["id"] == pid), ""))
                return int(nums[0]) if nums else None

            def plan(from_id: str, to_id: str, relation_type: str):
                if from_id == to_id:
                    return
                cats = {person["category"] for person in people if person["id"] in (from_id, to_id)}
                if "帝王" in cats and cats & {"朝臣", "将帅", "文苑"}:
                    return
                if relation_type in ("配偶", "兄弟姐妹") and from_id > to_id:
                    from_id, to_id = to_id, from_id
                key = (from_id, to_id, relation_type)
                if key in existing_pairs:
                    return
                fb, cb = birth_of(from_id), birth_of(to_id)
                if relation_type == "父子" and fb and cb and not (15 <= cb - fb <= 70):
                    return
                if relation_type == "母子" and fb and cb and not (13 <= cb - fb <= 55):
                    return
                if relation_type == "兄弟姐妹" and fb and cb and abs(fb - cb) > 20:
                    return
                existing_pairs.add(key)
                edges.append((from_id, to_id, relation_type, reign_by_id.get(to_id, "明代"), "哈佛 CBDB 亲属记录", source_id))

            for k in kinships:
                rel = (k.get("KinRelName") or "").strip()
                kin_name = t2s.convert(k.get("KinPersonName") or "")
                kin_name = re.sub(r"[（(].*?[)）]", "", kin_name).strip()
                candidates = name_to_ids.get(kin_name, [])
                if len(candidates) != 1:
                    continue
                target = candidates[0]["id"]
                for prefix, relation_type, direction in EDGE_RULES:
                    if rel.startswith(prefix):
                        if direction == "kin_to_self":
                            plan(target, person_id, relation_type)
                        else:
                            plan(person_id, target, relation_type)
                        break

            # 3) 生平追加仕历/出身（无维基全文的偏薄生平）
            current_life = life_content.get(person_id, "")
            if len(current_life) < 1200:
                extra = office_lines(postings) + entry_lines(entries)
                extra += [f"生卒与籍贯（据哈佛 CBDB）：{t2s.convert(basic.get('ChName', ''))}，"
                          f"籍贯{t2s.convert(basic.get('IndexAddr') or '未详')}，"
                          f"生卒{basic.get('YearBirth', '？')}—{basic.get('YearDeath', '？')}。"] if basic else []
                if extra:
                    marker = "〔《明史》原文"
                    shi_block = ""
                    if marker in current_life:
                        shi_block = current_life[current_life.index(marker):].strip()
                        current_life = current_life[:current_life.index(marker)].strip()
                    content = (current_life + "\n\n" if current_life else "") + "\n".join(dict.fromkeys(extra))
                    if shi_block:
                        content += "\n\n" + shi_block
                    db.execute(
                        "UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'life'",
                        (content, person_id),
                    )
                    life_enriched += 1
        time.sleep(0.35)

    with connect() as db:
        db.executemany(
            """
            INSERT OR IGNORE INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            edges,
        )
        total = db.execute("SELECT COUNT(*) FROM person_relation").fetchone()[0]
        family_ok = db.execute(
            "SELECT COUNT(DISTINCT person_id) FROM person_section WHERE section_key = 'family' AND content NOT LIKE '%史料未见详载%'"
        ).fetchone()[0]
    print(f"CBDB 身份确认 {resolved} 位；家族增强 {family_enriched} 位；新增关系 {len(edges)} 条（全库 {total}）；生平追加 {life_enriched} 位。", flush=True)
    print(f"家族栏目有实料：{family_ok}/748。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
