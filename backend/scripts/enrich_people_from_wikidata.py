#!/usr/bin/env python3
"""Build structured person profiles from exact Wikidata/Wikipedia matches.

The app stores only a concise, original synthesis of structured public facts. It
does not copy encyclopedia prose. Each successful match writes private audit
references; the mobile UI exposes only the verification state.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import connect, initialize_database  # noqa: E402

API = "https://www.wikidata.org/w/api.php"
SPARQL_API = "https://query.wikidata.org/sparql"
USER_AGENT = "LiangjingYishisanshengResearch/1.0 (historical educational app)"
ENTITY_PROPERTIES = {
    "birth": "P569",
    "death": "P570",
    "birth_place": "P19",
    "education": "P69",
    "occupation": "P106",
    "position": "P39",
    "father": "P22",
    "mother": "P25",
    "spouse": "P26",
    "child": "P40",
}


def api(params: dict[str, str]) -> dict:
    query = urlencode({"format": "json", **params})
    request = Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
        except URLError:
            if attempt == 3:
                raise
        time.sleep(3 * (attempt + 1))
    raise RuntimeError("维基数据请求重试耗尽")


def sparql_batch_matches(names_to_ids: dict[str, str]) -> dict[str, str]:
    """Fetch exact Chinese-label candidates in one request to avoid API throttling.

    Ambiguous names intentionally stay out of the result and fall back to the
    existing one-at-a-time matcher, where identity checks can reject collisions.
    """

    if not names_to_ids:
        return {}
    def literal(name: str) -> str:
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"@zh'

    literals = " ".join(literal(name) for name in names_to_ids)
    query = f"""
        SELECT ?person ?name WHERE {{
          VALUES ?name {{ {literals} }}
          ?person rdfs:label ?name .
        }}
    """
    request = Request(
        f"{SPARQL_API}?{urlencode({'format': 'json', 'query': query})}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                bindings = json.load(response).get("results", {}).get("bindings", [])
                candidates: dict[str, list[str]] = {}
                for binding in bindings:
                    name = binding.get("name", {}).get("value", "")
                    uri = binding.get("person", {}).get("value", "")
                    entity_id = uri.rsplit("/", 1)[-1]
                    if name in names_to_ids and entity_id.startswith("Q"):
                        candidates.setdefault(name, []).append(entity_id)
                return {
                    names_to_ids[name]: values[0]
                    for name, values in candidates.items()
                    if len(set(values)) == 1
                }
        except HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
        except URLError:
            if attempt == 3:
                raise
        time.sleep(3 * (attempt + 1))
    raise RuntimeError("维基数据批量查询重试耗尽")


def normalize(value: str) -> str:
    return re.sub(r"[\s·・．.（）()\-—]", "", value).replace("臺", "台")


def matching_entity(name: str) -> str | None:
    result = api({"action": "wbsearchentities", "search": name, "language": "zh", "limit": "10"})
    target = normalize(name)
    for candidate in result.get("search", []):
        names = [candidate.get("label", ""), candidate.get("match", {}).get("text", ""), *candidate.get("aliases", [])]
        if any(normalize(value) == target for value in names):
            return candidate["id"]
    return None


def entity_data(entity_ids: list[str]) -> dict[str, dict]:
    """通过 Special:EntityData 批量拉取实体（wbgetentities 被限流时的替代通道）。

    返回与 wbgetentities 相同的 claims/sitelinks 结构；失败的批次回退到 action API。
    """
    found: dict[str, dict] = {}
    for start in range(0, len(entity_ids), 20):
        batch = entity_ids[start : start + 20]
        request = Request(
            f"https://www.wikidata.org/wiki/Special:EntityData/{','.join(batch)}.json",
            headers={"User-Agent": USER_AGENT},
        )
        for attempt in range(4):
            try:
                with urlopen(request, timeout=20) as response:
                    found.update(json.load(response).get("entities", {}))
                break
            except (HTTPError, URLError, json.JSONDecodeError):
                if attempt == 3:
                    # 回退到 action API 批量拉取，保留原重试语义。
                    result = api(
                        {
                            "action": "wbgetentities",
                            "ids": "|".join(batch),
                            "props": "labels|descriptions|claims|sitelinks",
                            "languages": "zh|zh-hans|en",
                        }
                    )
                    found.update(result.get("entities", {}))
                    break
                time.sleep(3 * (attempt + 1))
    return found


def entities(entity_ids: list[str]) -> dict[str, dict]:
    return entity_data(entity_ids)


def entity_ids(entity: dict, property_id: str) -> list[str]:
    values = []
    for claim in entity.get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("id", "").startswith("Q"):
            values.append(value["id"])
    return list(dict.fromkeys(values))


def time_values(entity: dict, property_id: str) -> list[str]:
    values = []
    for claim in entity.get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and isinstance(value.get("time"), str):
            year = value["time"][1:5]
            if year.isdigit():
                values.append(year)
    return list(dict.fromkeys(values))


def label(entity: dict) -> str:
    labels = entity.get("labels", {})
    for language in ("zh-hans", "zh", "en"):
        if language in labels:
            return labels[language]["value"]
    return ""


def names(entity: dict, property_name: str, lookup: dict[str, dict]) -> list[str]:
    return [label(lookup[value]) for value in entity_ids(entity, ENTITY_PROPERTIES[property_name]) if value in lookup and label(lookup[value])]


def compatible_identity(person: sqlite3.Row, entity: dict, lookup: dict[str, dict]) -> bool:
    """Reject clear same-name collisions before synthesizing a profile."""

    text = " ".join(
        [
            *[entry.get("value", "") for entry in entity.get("descriptions", {}).values()],
            *names(entity, "occupation", lookup),
            *names(entity, "position", lookup),
        ]
    )
    expected_eunuch = "太监" in person["title"] or "宦官" in person["category"]
    expected_civil = "尚书" in person["title"] or "大学士" in person["title"]
    entity_eunuch = "宦官" in text or "太监" in text or "eunuch" in text.lower()
    entity_civil = "尚书" in text or "大学士" in text or "minister" in text.lower()
    expected_years = [int(value) for value in re.findall(r"\d{4}", person["years"])]
    actual_birth = [int(value) for value in time_values(entity, ENTITY_PROPERTIES["birth"])]
    actual_death = [int(value) for value in time_values(entity, ENTITY_PROPERTIES["death"])]
    chronology_conflict = (
        (expected_years and actual_birth and abs(expected_years[0] - actual_birth[0]) > 5)
        or (len(expected_years) > 1 and actual_death and abs(expected_years[-1] - actual_death[0]) > 5)
    )
    return not (chronology_conflict or (expected_eunuch and entity_civil) or (expected_civil and entity_eunuch))


def qualifier_year(claim: dict, property_id: str) -> str:
    """职位／教育声明的起止年限定符（P580／P582）。"""
    for snak in claim.get("qualifiers", {}).get(property_id, []):
        value = snak.get("datavalue", {}).get("value")
        if isinstance(value, dict) and isinstance(value.get("time"), str):
            year = value["time"][1:5]
            if year.isdigit():
                return year
    return ""


def office_timeline(entity: dict, lookup: dict[str, dict]) -> list[str]:
    """把 P39 职位按起止年排序成任职经历时间线，弥补生平正文缺少仕历结构的问题。"""
    rows: list[tuple[int, str]] = []
    for claim in entity.get("claims", {}).get(ENTITY_PROPERTIES["position"], []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if not isinstance(value, dict) or not value.get("id", "").startswith("Q"):
            continue
        title = label(lookup.get(value["id"], {}))
        if not title:
            continue
        start = qualifier_year(claim, "P580")
        end = qualifier_year(claim, "P582")
        span = f"（{start}—{end}）" if (start or end) else ""
        rows.append((int(start or "9999"), f"{title}{span}"))
    rows.sort(key=lambda row: row[0])
    return [row[1] for row in rows]


def profile_text(person: sqlite3.Row, entity: dict, lookup: dict[str, dict]) -> tuple[str, str]:
    birth = time_values(entity, ENTITY_PROPERTIES["birth"])
    death = time_values(entity, ENTITY_PROPERTIES["death"])
    birth_place = names(entity, "birth_place", lookup)
    education = names(entity, "education", lookup)
    occupation = names(entity, "occupation", lookup)
    positions = names(entity, "position", lookup)
    timeline = office_timeline(entity, lookup)
    details = []
    if birth or death:
        details.append(f"公开资料记录的生卒信息为“{'—'.join([birth[0] if birth else '？', death[0] if death else '？'])}”。")
    if birth_place:
        details.append(f"出生地相关记录指向{birth_place[0]}。")
    if education:
        details.append(f"教育背景可查为{education[0]}。")
    if occupation:
        details.append(f"资料将其身份概括为{'、'.join(occupation[:3])}。")
    if positions:
        details.append(f"公开任职记录包括{'、'.join(positions[:4])}。")
    if timeline:
        details.append("任职经历按起止年排列：" + "；".join(timeline[:8]) + "。")
    life = re.sub(
        r"本条已建立人物、年号与资料来源的关联；具体仕历、卷次和原文引文仍待编辑校核。",
        "",
        person["biography"],
    ).strip()
    if details:
        life = f"{life}\n\n" + "".join(details)

    family_parts = []
    family_labels = (("father", "父亲"), ("mother", "母亲"), ("spouse", "配偶"), ("child", "子女"))
    for key, title in family_labels:
        values = names(entity, key, lookup)
        if values:
            family_parts.append(f"{title}：{'、'.join(values)}。")
    return life, "".join(family_parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="从 Wikidata 精确匹配建立人物生平与家族资料")
    parser.add_argument("--all", action="store_true", help="处理所有人物；默认只处理首批核心人物")
    parser.add_argument(
        "--source-id",
        help="只处理指定来源的人物；例如 cbdb-20210525。与 --all 不能同时使用。",
    )
    parser.add_argument(
        "--unverified-only",
        action="store_true",
        help="只复核当前仍标记为“未校验”的人物。",
    )
    parser.add_argument(
        "--pending-only",
        action="store_true",
        help="只处理尚未完成精确匹配、未找到或身份排除判断的人物；网络失败会保留在待处理队列。",
    )
    parser.add_argument(
        "--batch-search",
        action="store_true",
        help="先通过 Wikidata Query Service 批量查询精确中文名称，再回退到单条检索。",
    )
    parser.add_argument("--ids", help="只处理指定的逗号分隔人物 ID（与 --all/--source-id 互斥）")
    parser.add_argument("--limit", type=int, default=0, help="限制处理条数，0 表示不限制")
    parser.add_argument("--offset", type=int, default=0, help="跳过前若干条，用于分批持久化")
    parser.add_argument("--sleep", type=float, default=1.5, help="每次检索之间的等待秒数")
    args = parser.parse_args()

    initialize_database()
    if args.all and args.source_id:
        parser.error("--all 与 --source-id 不能同时使用")
    if args.ids and (args.all or args.source_id):
        parser.error("--ids 不能与 --all/--source-id 同时使用")
    conditions: list[str] = []
    parameters: list[str] = []
    if args.ids:
        ids = [item.strip() for item in args.ids.split(",") if item.strip()]
        conditions.append(f"id IN ({', '.join('?' * len(ids))})")
        parameters.extend(ids)
    elif args.source_id:
        conditions.append("source_id = ?")
        parameters.append(args.source_id)
    elif not args.all:
        conditions.append("source_id <> 'cbdb-20210525'")
    if args.unverified_only:
        conditions.append("verification_status = '未校验'")
    if args.pending_only:
        conditions.append(
            """NOT EXISTS (
                SELECT 1 FROM person_research AS research
                WHERE research.person_id = person.id
                  AND research.provider = 'wikidata'
                  AND research.status IN ('matched', 'not_found', 'identity_rejected')
            )"""
        )
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with connect() as db:
        people = db.execute(f"SELECT * FROM person {where} ORDER BY id", parameters).fetchall()
    people = people[args.offset :]
    if args.limit:
        people = people[: args.limit]

    matches: dict[str, str] = {}
    outcomes: dict[str, tuple[str, str]] = {}
    if args.batch_search:
        try:
            matches = sparql_batch_matches({person["name"]: person["id"] for person in people})
            for person_id in matches:
                outcomes[person_id] = ("matched", "Wikidata Query Service 精确中文名称匹配")
            print(f"批量精确名称匹配：{len(matches)}/{len(people)}", flush=True)
        except Exception as error:
            print(f"批量检索失败，将回退至单条检索（{error}）", flush=True)
    for index, person in enumerate(people, start=1):
        if person["id"] in matches:
            continue
        try:
            entity_id = matching_entity(person["name"])
        except Exception as error:  # Network errors leave this record untouched for a later retry.
            outcomes[person["id"]] = ("network_failed", str(error))
            print(f"[{index}/{len(people)}] {person['name']}: 检索失败（{error}）", flush=True)
            continue
        if entity_id:
            matches[person["id"]] = entity_id
            print(f"[{index}/{len(people)}] {person['name']}: {entity_id}", flush=True)
        else:
            outcomes[person["id"]] = ("not_found", "未找到中文名称的精确实体匹配")
            print(f"[{index}/{len(people)}] {person['name']}: 未找到精确匹配", flush=True)
        time.sleep(args.sleep)

    entity_map = entities(list(matches.values()))
    related_ids = {
        value
        for entity in entity_map.values()
        for property_id in ENTITY_PROPERTIES.values()
        for value in entity_ids(entity, property_id)
    }
    lookup = {**entity_map, **entities(sorted(related_ids))}

    with connect() as db:
        for person in people:
            person_id = person["id"]
            entity_id = matches.get(person_id)
            entity = entity_map.get(entity_id, {})
            if entity_id and compatible_identity(person, entity, lookup):
                life, family = profile_text(person, entity, lookup)
                verification = "已校验" if "zhwiki" in entity.get("sitelinks", {}) else "未校验"
                outcome = ("matched", entity_id)
            else:
                entity_id = None
                life = re.sub(
                    r"本条已建立人物、年号与资料来源的关联；具体仕历、卷次和原文引文仍待编辑校核。",
                    "",
                    person["biography"],
                ).strip()
                family = ""
                verification = "未校验"
                outcome = outcomes.get(person_id, ("identity_rejected", "同名实体与人物年代或身份不一致"))
            db.execute(
                "UPDATE person SET biography = ?, family_summary = ?, verification_status = ? WHERE id = ?",
                (life, family, verification, person_id),
            )
            db.executemany(
                """
                INSERT INTO person_section(person_id, section_key, title, position, content)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(person_id, section_key) DO UPDATE SET title = excluded.title, position = excluded.position, content = excluded.content
                """,
                [
                    (person_id, "life", "生平（含教育背景）", 0, life),
                    (person_id, "family", "家族与子嗣", 1, family),
                    (person_id, "verification", "资料状态", 2, verification),
                ],
            )
            db.executemany(
                """
                INSERT INTO content_reference(content_type, content_id, section_key, position, title, url, locator, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_type, content_id, section_key, position) DO UPDATE SET
                    title = excluded.title, url = excluded.url, locator = excluded.locator, note = excluded.note
                """,
                [
                    ("person", person_id, "life", 1, "中文维基百科检索", f"https://zh.wikipedia.org/wiki/{quote(person['name'])}", person["name"], "用于人工复核"),
                    ("person", person_id, "life", 2, "百度百科检索", f"https://baike.baidu.com/search/word?word={quote(person['name'])}", person["name"], "用于人工复核"),
                ] + ([
                    ("person", person_id, "life", 0, "维基数据人物条目", f"https://www.wikidata.org/wiki/{entity_id}", entity_id, "结构化资料交叉检索"),
                ] if entity_id else []),
            )
            db.execute(
                """
                INSERT INTO person_research(person_id, provider, status, entity_id, checked_at, note)
                VALUES (?, 'wikidata', ?, ?, ?, ?)
                ON CONFLICT(person_id, provider) DO UPDATE SET
                    status = excluded.status,
                    entity_id = excluded.entity_id,
                    checked_at = excluded.checked_at,
                    note = excluded.note
                """,
                (
                    person_id,
                    outcome[0],
                    entity_id or "",
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    outcome[1],
                ),
            )
    print(f"完成：{len(matches)}/{len(people)} 位人物获得精确维基数据匹配。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
