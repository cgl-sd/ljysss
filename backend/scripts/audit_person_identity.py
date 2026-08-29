#!/usr/bin/env python3
"""人物身份判定：按姓名合并造成的错配必须撤销，非明代条目必须清除。

判据不是「名字相同」，而是姓名＋字号＋籍贯＋生卒区间四者相容。四道硬信号：

1. 正文是维基消歧义页或重定向页 —— 它根本不是一个人。
2. 生卒年落在明代范围外 —— 直接证伪。
3. 正文开头自报他朝身份（「西汉…将领」「南宋…名臣」）—— 直接证伪。
4. 挂着《明史》锚点，但《明史》本文里的字号或籍贯与库内正文对不上 ——
   说明锚点属于另一个同名明人（如明史卷175 的卫青是松江华亭人、字明德，
   而库里正文是字仲卿、河东平阳人的汉将），锚点与据此回填的年号一律撤销。

    backend/.venv/bin/python backend/scripts/audit_person_identity.py            # 只报告
    backend/.venv/bin/python backend/scripts/audit_person_identity.py --apply    # 执行
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
CONTENT = BACKEND / "data" / "content"
STAGING = BACKEND / "data" / "staging"

t2s = OpenCC("t2s")

TABLES = ["source", "reign", "person", "event", "event_section", "person_section",
          "content_reference", "person_research", "person_relation", "institution",
          "institution_promotion", "institution_reform", "special_item",
          "person_mingshi", "person_wiki", "person_cbdb"]

DISAMBIGUATION = re.compile(r"可以指|是一个重定向|（消歧义）|\(消歧义\)")
# 自报他朝：朝代词紧跟身份词，且中间不超过 12 字
SELF_OTHER_DYNASTY = re.compile(
    r"(西汉|东汉|南宋|北宋|秦朝|汉朝|晋朝|隋朝|唐朝|唐代|宋代|宋朝|元代|元朝|三国|清朝|清代)"
    r"[^\n，。]{0,12}?(?:将领|名臣|大臣|皇帝|政治家|学者|官员|人物|宗室|大臣|宰相|进士)")
MING_SELF = re.compile(r"(明朝|明代|明初|明末|元末明初)")
ZI = re.compile(r"字([^\s，。；、（）「」“”·]{1,5})")
NATIVE = re.compile(r"([\u4e00-\u9fff]{2,8}?)(?:人|籍)[，。\n]")
BIRTH = re.compile(r"^\s*(\d{4})—")


def load(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(table: str, rows: list[dict]) -> None:
    (CONTENT / f"{table}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def given_name(text: str) -> str:
    match = ZI.search(text or "")
    return match.group(1) if match else ""


def native_place(text: str) -> str:
    match = NATIVE.search((text or "")[:200])
    return match.group(1) if match else ""


def text_mismatch(person: dict, anchor: dict) -> str:
    """高置信的正文错配：消歧义页，或正文自报他朝身份。

    字号与籍贯比对不做自动改写——维基白话里「株连一万五千人」会被当成籍贯，
    「字行，以字行」会让字号取到不同成分，误判代价是把好正文换成明史摘句。
    """

    bio = person.get("biography") or ""
    if DISAMBIGUATION.search(bio):
        return "正文是消歧义页"
    other = SELF_OTHER_DYNASTY.search(bio[:220])
    if other and not MING_SELF.search(bio[:220]):
        return f"正文自报{other.group(1)}身份"
    return ""


def needs_review(person: dict, anchor: dict) -> str:
    """可疑但不足以自动改写的，只列出来交人工判定。"""

    bio = person.get("biography") or ""
    mine, theirs = given_name(bio), given_name(anchor["opening"])
    if mine and theirs and mine not in ("行", "一字") and theirs not in ("行", "一字") \
            and mine not in theirs and theirs not in mine:
        return f"字号待核：明史「{theirs}」/ 本文「{mine}」"
    return ""


def classify(person: dict, anchor: dict | None) -> tuple[str, str]:
    """返回 (判定, 理由)。

    以《明史》名录为轴：在册的人一律保留，正文对不上是正文的错（挂成了同名
    他人的文字），判 fix-text 用明史本文替换；不在册的人才谈得上「不是明人」，
    按消歧义页、生卒越界、自报他朝三条证伪。
    """
    bio = person.get("biography") or ""

    if anchor:
        mismatch = text_mismatch(person, anchor)
        if mismatch:
            return "fix-text", mismatch
        review = needs_review(person, anchor)
        if review:
            return "review", review
        return "keep", ""

    if DISAMBIGUATION.search(bio):
        return "delete", "正文是消歧义页或重定向页，不是一个人"
    match = BIRTH.match(person.get("years") or "")
    if match and not 1295 <= int(match.group(1)) <= 1670:
        return "delete", f"生卒 {person['years']} 落在明代范围外"
    other = SELF_OTHER_DYNASTY.search(bio[:220])
    if other and not MING_SELF.search(bio[:220]):
        return "delete", f"正文自报{other.group(1)}身份"
    return "keep", ""


def main(apply: bool) -> None:
    roster: dict[str, dict] = {}
    for line in (STAGING / "persons.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            roster.setdefault(t2s.convert(entry["name"]), entry)

    tables = {name: load(name) for name in TABLES}

    verdicts: dict[str, tuple[str, str]] = {}
    for person in tables["person"]:
        verdicts[person["id"]] = classify(person, roster.get(person["name"]))

    counts = Counter(verdict for verdict, _ in verdicts.values())
    print(f"人物 {len(verdicts)}：{dict(counts)}")
    by_reason: dict[str, list[str]] = {}
    for person in tables["person"]:
        verdict, reason = verdicts[person["id"]]
        if verdict != "keep":
            by_reason.setdefault(f"{verdict}｜{reason.split('：')[0]}", []).append(person["name"])
    print("\n判定分组：")
    for reason, names_list in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        print(f"  {reason:<28} {len(names_list):>4}  例: {'、'.join(names_list[:6])}")
    if not apply:
        print("\n未执行。加 --apply 生效。")
        return

    doomed = {p["id"] for p in tables["person"] if verdicts[p["id"]][0] == "delete"}
    names = {p["id"]: p["name"] for p in tables["person"] if p["id"] in doomed}
    tables["person"] = [p for p in tables["person"] if p["id"] not in doomed]

    fixed = 0
    for person in tables["person"]:
        verdict, _ = verdicts[person["id"]]
        if verdict != "fix-text":
            continue
        entry = roster.get(person["name"])
        opening = (entry or {}).get("opening", "").strip()
        if not opening:
            continue
        block = f"〔《明史》原文〕\n{opening[:900]}"
        person["biography"] = f"{opening[:1200]}\n\n{block}"
        person["summary"] = opening[:120]
        if entry.get("era"):
            person["reign"] = entry["era"]
        life = next((row for row in tables["person_section"]
                     if row.get("person_id") == person["id"] and row.get("section_key") == "life"), None)
        if life:
            life["content"] = person["biography"]
        for row in tables["content_reference"]:
            if row.get("content_type") == "person" and row.get("content_id") == person["id"]:
                row["url"] = ""
                row["note"] = f"正文改用《明史》本文（原判：{(verdicts[person['id']][1])}）"
        fixed += 1
    print(f"正文错配已改用《明史》本文：{fixed} 人")

    drop_by_person = {
        "person_section": "person_id", "person_wiki": "person_id", "person_mingshi": "person_id",
        "person_cbdb": "person_id", "person_research": "person_id",
    }
    for table, field in drop_by_person.items():
        tables[table] = [r for r in tables[table] if r.get(field) not in doomed]
    tables["content_reference"] = [
        r for r in tables["content_reference"]
        if not (r.get("content_type") == "person" and r.get("content_id") in doomed)]
    tables["person_relation"] = [
        r for r in tables["person_relation"]
        if r.get("from_person_id") not in doomed and r.get("to_person_id") not in doomed]
    for event in tables["event"]:
        people = [n for n in (event.get("participants") or "").split("、") if n.strip()]
        event["participants"] = "、".join(n for n in people if n not in names.values())

    for name, rows in tables.items():
        dump(name, rows)
    (STAGING / "identity_verdicts.json").write_text(
        json.dumps({k: {"verdict": v, "reason": r} for k, (v, r) in verdicts.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已删除 {len(doomed)} 人，库内人物 {len(tables['person'])}；判决留档 identity_verdicts.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    main(parser.parse_args().apply)
