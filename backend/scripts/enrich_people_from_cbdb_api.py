#!/usr/bin/env python3
"""Build factual Ming-person profiles from the official CBDB person API.

CBDB responses are structured records with original source and page metadata.
This importer produces an original, concise synthesis for the app and keeps the
source link in the private audit table. It never invents a narrative where the
record only supplies a name or date.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import connect, initialize_database  # noqa: E402

API = "https://cbdb.fas.harvard.edu/cbdbapi/person.php?id={person_id}&o=json"
USER_AGENT = "LiangjingYishisanshengResearch/1.0 (historical educational app)"


def listify(value: object, key: str) -> list[dict]:
    if not isinstance(value, dict):
        return []
    entries = value.get(key, [])
    if isinstance(entries, dict):
        return [entries]
    return entries if isinstance(entries, list) else []


def fetch(person_id: str) -> dict:
    request = Request(API.format(person_id=person_id), headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)
                return payload["Package"]["PersonAuthority"]["PersonInfo"]["Person"]
        except (HTTPError, URLError, KeyError, json.JSONDecodeError) as error:
            if attempt == 3:
                raise RuntimeError(str(error)) from error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("CBDB API 重试耗尽")


def nonempty(*values: object) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip() and str(value).strip() not in {"未詳", "[n/a]"}]


def profile(person: dict, fallback_name: str, fallback_years: str) -> tuple[str, str, list[str]]:
    basic = person.get("BasicInfo", {}) if isinstance(person.get("BasicInfo"), dict) else {}
    name = str(basic.get("ChName") or fallback_name)
    birth = str(basic.get("YearBirth") or "")
    death = str(basic.get("YearDeath") or "")
    years = f"{birth}—{death}" if birth and death else fallback_years
    life: list[str] = [f"{name}（{years}）已由中国历代人物传记资料库的个人档案核验。"]
    addresses = listify(person.get("PersonAddresses"), "Address")
    places = list(dict.fromkeys(entry["AddrName"] for entry in addresses if entry.get("AddrName")))
    aliases = listify(person.get("PersonAliases"), "Alias")
    alias_text = [f"{entry.get('AliasType', '别名')}“{entry['AliasName']}”" for entry in aliases if entry.get("AliasName")]
    facts = []
    if places:
        facts.append(f"籍贯或相关地址记为{'、'.join(places[:3])}")
    if alias_text:
        facts.append("、".join(alias_text[:3]))
    if facts:
        life.append("；".join(facts) + "。")
    entries = listify(person.get("PersonEntryInfo"), "Entry")
    entry_names = list(dict.fromkeys(entry.get("EntryName", "") for entry in entries if entry.get("EntryName")))
    if entry_names:
        life.append(f"教育或科举记录包括{'、'.join(entry_names[:4])}。")
    postings = listify(person.get("PersonPostings"), "Posting")
    offices = list(dict.fromkeys(entry.get("OfficeName", "") for entry in postings if entry.get("OfficeName")))
    if offices:
        life.append(f"仕历记录包括{'、'.join(offices[:6])}。")
    if len(life) == 1:
        life.append("现有公开档案仅提供基础年代与索引信息，具体教育、仕历和事迹仍待进一步补充。")

    kinship = listify(person.get("PersonKinshipInfo"), "Kinship")
    groups: dict[str, list[str]] = {"父亲": [], "母亲": [], "配偶": [], "子女": []}
    for entry in kinship:
        relation = str(entry.get("KinRelName") or "")
        relative = str(entry.get("KinPersonName") or "")
        if not relative:
            continue
        if relation in {"父", "父親"}:
            groups["父亲"].append(relative)
        elif relation in {"母", "母親"}:
            groups["母亲"].append(relative)
        elif "妻" in relation or "夫" in relation:
            groups["配偶"].append(relative)
        elif relation in {"子", "女兒", "女"} or "嗣子" in relation:
            groups["子女"].append(relative)
    family = "".join(
        f"{label}：{'、'.join(dict.fromkeys(relatives))}。"
        for label, relatives in groups.items()
        if relatives
    ) or "公开档案尚未列出可确认的家族与子嗣资料。"
    sources = [entry.get("Source", "") for entry in listify(person.get("PersonSources"), "Source")]
    return "".join(life), family, [source for source in sources if source]


def main() -> int:
    parser = argparse.ArgumentParser(description="从官方 CBDB API 批量建立人物档案")
    parser.add_argument("--limit", type=int, default=0, help="处理条数；0 表示全部")
    parser.add_argument("--offset", type=int, default=0, help="跳过前若干条")
    parser.add_argument("--sleep", type=float, default=0.1, help="请求间隔秒数")
    parser.add_argument("--workers", type=int, default=4, help="并发请求数，默认 4")
    parser.add_argument("--pending-only", action="store_true", help="跳过已经由 CBDB API 核验的人物")
    args = parser.parse_args()

    initialize_database()
    condition = ""
    if args.pending_only:
        condition = """
            AND NOT EXISTS (
                SELECT 1 FROM person_research AS research
                WHERE research.person_id = person.id
                  AND research.provider = 'cbdb_api'
                  AND research.status = 'matched'
            )
        """
    with connect() as db:
        people = db.execute(
            f"""
            SELECT id, name, years FROM person
            WHERE source_id = 'cbdb-20210525' {condition}
            ORDER BY id
            """
        ).fetchall()
    people = people[args.offset :]
    if args.limit:
        people = people[: args.limit]

    if args.workers < 1 or args.workers > 8:
        parser.error("--workers 必须介于 1 和 8 之间")

    def retrieve(item: sqlite3.Row) -> tuple[sqlite3.Row, dict | None, str]:
        person_id = item["id"].removeprefix("cbdb-")
        try:
            record = fetch(person_id)
            return item, record, ""
        except RuntimeError as error:
            return item, None, str(error)

    records: list[tuple[sqlite3.Row, dict | None, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for index, (item, record, error) in enumerate(executor.map(retrieve, people), start=1):
            records.append((item, record, error))
            if record is None:
                print(f"[{index}/{len(people)}] {item['name']}: 检索失败（{error}）", flush=True)
            else:
                print(f"[{index}/{len(people)}] {item['name']}: 已取得 CBDB 档案", flush=True)
            time.sleep(args.sleep)

    with connect() as db:
        for item, record, error in records:
            source_id = item["id"].removeprefix("cbdb-")
            checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if record is None:
                db.execute(
                    """
                    INSERT INTO person_research(person_id, provider, status, entity_id, checked_at, note)
                    VALUES (?, 'cbdb_api', 'network_failed', '', ?, ?)
                    ON CONFLICT(person_id, provider) DO UPDATE SET
                        status = excluded.status, checked_at = excluded.checked_at, note = excluded.note
                    """,
                    (item["id"], checked_at, error),
                )
                continue
            life, family, sources = profile(record, item["name"], item["years"])
            note = "；".join(sources[:4]) or "官方 CBDB 个人档案"
            db.execute(
                """
                UPDATE person SET biography = ?, family_summary = ?, verification_status = '已校验'
                WHERE id = ?
                """,
                (life, family, item["id"]),
            )
            db.executemany(
                """
                INSERT INTO person_section(person_id, section_key, title, position, content)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(person_id, section_key) DO UPDATE SET
                    title = excluded.title, position = excluded.position, content = excluded.content
                """,
                [
                    (item["id"], "life", "生平（含教育背景）", 0, life),
                    (item["id"], "family", "家族与子嗣", 1, family),
                    (item["id"], "verification", "资料状态", 2, "已校验"),
                ],
            )
            db.executemany(
                """
                INSERT INTO content_reference(content_type, content_id, section_key, position, title, url, locator, note)
                VALUES ('person', ?, ?, ?, 'CBDB 人物档案', ?, ?, ?)
                ON CONFLICT(content_type, content_id, section_key, position) DO UPDATE SET
                    title = excluded.title, url = excluded.url, locator = excluded.locator, note = excluded.note
                """,
                [
                    (item["id"], "life", 3, API.format(person_id=source_id), source_id, note),
                    (item["id"], "family", 2, API.format(person_id=source_id), source_id, note),
                ],
            )
            db.execute(
                """
                INSERT INTO person_research(person_id, provider, status, entity_id, checked_at, note)
                VALUES (?, 'cbdb_api', 'matched', ?, ?, ?)
                ON CONFLICT(person_id, provider) DO UPDATE SET
                    status = excluded.status, entity_id = excluded.entity_id,
                    checked_at = excluded.checked_at, note = excluded.note
                """,
                (item["id"], source_id, checked_at, note),
            )
    matched = sum(record is not None for _, record, _ in records)
    print(f"完成：{matched}/{len(records)} 位人物获得官方 CBDB 档案。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
