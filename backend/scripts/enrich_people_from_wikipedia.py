#!/usr/bin/env python3
"""以中文维基百科为主线，为全部人物建立详细生平。

流程：
1. 优先复用 person_research 中已通过的维基数据精确匹配；其余人物先用
   Wikidata Query Service 批量匹配精确中文名，再回退单条检索，全部经过
   年代与身份兼容校验（compatible_identity），杜绝同名错撞。
2. 取匹配实体的 zhwiki sitelink，按条目标题批量抓取中文维基百科导语
   （纯文本），与维基数据结构化事实（生卒、籍贯、教育、任职时间线）
   一起做原创综述；不照抄百科正文。
3. 写库：已有“生平”栏目的 56 位核心人物保持不动；其余人物写入结构化
   “生平”栏目；模板占位的 biography 一并替换。“家族与子嗣”栏目一律
   不动（结局内容为人工校订，禁止被本脚本覆盖）。
4. 校验标记沿用项目规则：条目存在 zhwiki sitelink 才标“已校验”。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import connect, initialize_database  # noqa: E402
from enrich_people_from_wikidata import (  # noqa: E402
    compatible_identity,
    entity_data,
    entity_ids,
    label,
    matching_entity,
    names,
    office_timeline,
    time_values,
)

WIKI_API = "https://zh.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "LiangjingYishisanshengResearch/1.0 (historical educational app)"
PROPERTY_IDS = {
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
    "manner_of_death": "P1196",
    "cause_of_death": "P509",
}
STUB_MARKERS = ("活动于", "时期，身份为")


def api(host: str, params: dict[str, str]) -> dict:
    query = "&".join(f"{key}={quote(str(value))}" for key, value in params.items())
    request = Request(f"{host}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            # DNS 解析没有超时概念，污染或丢包时 getaddrinfo 可能无限挂起；
            # 用线程看门狗把单次请求硬性限制在 30 秒内。
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(urlopen, request, None, 20)
                with future.result(timeout=30) as response:
                    return json.load(response)
        except FuturesTimeoutError:
            raise TimeoutError(f"{host} 请求超过 30 秒")
        except HTTPError as error:
            if error.code not in (429, 503) or attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
        except (URLError, TimeoutError):
            # 连接级失败多为平台故障：快速跳过，让单条人物失败不拖垮整批。
            if attempt >= 1:
                raise
            time.sleep(3)
    raise RuntimeError("请求重试耗尽")


def zh_wikipedia_reachable() -> bool:
    """单次轻量探活；维基媒体偶发平台级故障时切换为纯维基数据通道。"""

    try:
        api(
            WIKI_API,
            {"action": "query", "meta": "siteinfo", "format": "json", "formatversion": "2"},
        )
        return True
    except Exception:
        return False


def search_zh_article(name: str) -> str | None:
    """在中文维基百科检索人物条目；优先标题精确等于姓名的结果。"""

    result = api(
        WIKI_API,
        {
            "action": "query",
            "list": "search",
            "srsearch": name,
            "srlimit": "5",
            "srnamespace": "0",
            "format": "json",
            "formatversion": "2",
        },
    )
    titles = [item.get("title", "") for item in result.get("query", {}).get("search", [])]
    for title in titles:
        if title == name:
            return title
    for title in titles:
        if name in title:
            return title
    return titles[0] if titles else None


def entities_by_zh_titles(titles: list[str]) -> dict[str, dict]:
    """用 wbgetentities(sites=zhwiki) 批量把条目标题解析为维基数据实体。"""

    found: dict[str, dict] = {}
    for start in range(0, len(titles), 30):
        batch = titles[start : start + 30]
        result = api(
            WIKIDATA_API,
            {
                "action": "wbgetentities",
                "sites": "zhwiki",
                "titles": "|".join(batch),
                "props": "claims|sitelinks",
                "format": "json",
                "formatversion": "2",
            },
        )
        for entity in (result.get("entities") or {}).values():
            if not isinstance(entity, dict) or "missing" in entity:
                continue
            title = entity.get("sitelinks", {}).get("zhwiki", {}).get("title")
            if title:
                found[title] = entity
        time.sleep(0.4)
    return found


def wiki_extracts(titles: list[str]) -> dict[str, str]:
    """按标题批量抓取中文维基百科导语纯文本，最多每批 20 条。"""

    found: dict[str, str] = {}
    for start in range(0, len(titles), 20):
        batch = titles[start : start + 20]
        result = api(
            WIKI_API,
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "extracts",
                "exintro": "1",
                "explaintext": "1",
                "exlimit": "20",
                "redirects": "1",
                "format": "json",
                "formatversion": "2",
            },
        )
        for page in result.get("query", {}).get("pages", []):
            extract = (page.get("extract") or "").strip()
            if extract and "missing" not in page:
                found[page["title"]] = extract
        time.sleep(0.4)
    return found


def property_values(entity: dict, property_id: str, lookup: dict[str, dict]) -> list[str]:
    return [
        label(lookup[value])
        for value in entity_ids(entity, property_id)
        if value in lookup and label(lookup[value])
    ]


def digested_facts(person, entity: dict, lookup: dict[str, dict]) -> str:
    """把维基数据结构化声明整理成原创综述段落（不使用百科原句）。"""

    birth = time_values(entity, PROPERTY_IDS["birth"])
    death = time_values(entity, PROPERTY_IDS["death"])
    timeline = office_timeline(entity, lookup)
    details: list[str] = []
    if birth or death:
        details.append(f"生卒年份可考为{'—'.join([birth[0] if birth else '？', death[0] if death else '？'])}年。")
    birth_place = property_values(entity, PROPERTY_IDS["birth_place"], lookup)
    if birth_place:
        details.append(f"籍贯指向{birth_place[0]}。")
    education = property_values(entity, PROPERTY_IDS["education"], lookup)
    if education:
        details.append(f"教育背景可查为{education[0]}。")
    occupation = property_values(entity, PROPERTY_IDS["occupation"], lookup)
    if occupation:
        details.append(f"身份被概括为{'、'.join(occupation[:3])}。")
    if timeline:
        details.append("任职经历按起止年排列：" + "；".join(timeline[:8]) + "。")
    for property_id, wording in (
        (PROPERTY_IDS["manner_of_death"], "死亡方式记载为"),
        (PROPERTY_IDS["cause_of_death"], "死因记载为"),
    ):
        values = property_values(entity, property_id, lookup)
        if values:
            details.append(f"{wording}{values[0]}。")
    return "".join(details)


def main() -> int:
    parser = argparse.ArgumentParser(description="以中文维基百科为主线补全人物生平")
    parser.add_argument("--sleep", type=float, default=0.35, help="条目检索之间的等待秒数")
    parser.add_argument("--limit", type=int, default=0, help="限制处理条数，0 表示不限制")
    args = parser.parse_args()

    initialize_database()
    with connect() as db:
        people = db.execute(
            """
            SELECT person.*, research.entity_id AS wikidata_entity
            FROM person
            LEFT JOIN person_research research
              ON research.person_id = person.id AND research.provider = 'wikidata' AND research.status = 'matched'
            ORDER BY person.id
            """
        ).fetchall()
        sectioned = {
            row["person_id"]
            for row in db.execute("SELECT DISTINCT person_id FROM person_section WHERE section_key = 'life'")
        }
    people = people[: args.limit] if args.limit else people
    already_matched = {p["id"]: p["wikidata_entity"] for p in people if p["wikidata_entity"]}
    print(f"待处理人物 {len(people)} 位，其中已有维基数据匹配 {len(already_matched)} 位。", flush=True)

    # ---- 1. 条目/实体匹配：中文维基百科可达时按条目检索，不可达或中途失效时逐条匹配维基数据 ----
    zh_channel = zh_wikipedia_reachable()
    print(f"中文维基百科可达性：{zh_channel}。", flush=True)
    candidate_ids: dict[str, str] = {}
    title_of: dict[str, str] = {}
    pending = [p for p in people if p["id"] not in already_matched]
    consecutive_failures = 0
    for index, person in enumerate(pending, start=1):
        if zh_channel:
            try:
                title = search_zh_article(person["name"])
                consecutive_failures = 0
                if title:
                    title_of[person["id"]] = title
            except Exception as error:
                consecutive_failures += 1
                print(f"[{index}/{len(pending)}] {person['name']}: 检索失败（{error}）", flush=True)
                if consecutive_failures >= 5 and not zh_wikipedia_reachable():
                    zh_channel = False
                    print("中文维基百科通道失效，切换维基数据逐条匹配。", flush=True)
        else:
            try:
                entity_id = matching_entity(person["name"])
                consecutive_failures = 0
                if entity_id:
                    candidate_ids[person["id"]] = entity_id
            except Exception as error:
                consecutive_failures += 1
                print(f"[{index}/{len(pending)}] {person['name']}: 匹配失败（{error}）", flush=True)
                if consecutive_failures >= 5:
                    print("维基数据通道也失效，中止本轮；网络恢复后重跑即可续传。", flush=True)
                    break
        if index % 100 == 0:
            channel = "条目检索" if zh_channel else "实体匹配"
            print(f"已{channel} {index}/{len(pending)}，命中 {len(candidate_ids) + len(title_of)}。", flush=True)
        time.sleep(args.sleep)
    if zh_channel:
        resolved_by_title = entities_by_zh_titles(sorted(set(title_of.values())))
        for person_id, title in title_of.items():
            entity = resolved_by_title.get(title)
            if entity and entity.get("id"):
                candidate_ids[person_id] = entity["id"]
        print(f"条目检索命中 {len(title_of)}/{len(pending)}。", flush=True)
    else:
        print(f"维基数据逐条匹配命中 {len(candidate_ids)}/{len(pending)}。", flush=True)

    # ---- 2. 实体拉取 + 身份兼容校验 ----
    existing_entities = entity_data(sorted(set(already_matched.values())))
    candidate_entities = entity_data(sorted(set(candidate_ids.values())))
    entity_by_id = {
        entity["id"]: entity
        for entity in [*existing_entities.values(), *candidate_entities.values()]
        if entity.get("id")
    }
    related_ids = {
        value
        for entity in entity_by_id.values()
        for property_id in PROPERTY_IDS.values()
        for value in entity_ids(entity, property_id)
    }
    lookup = {**entity_by_id, **entity_data(sorted(related_ids))}

    accepted: dict[str, str] = {}
    entity_of: dict[str, dict] = {}
    rejected = 0
    for person in people:
        person_id = person["id"]
        entity_id = already_matched.get(person_id) or candidate_ids.get(person_id)
        if not entity_id:
            continue
        entity = entity_by_id.get(entity_id)
        if entity and compatible_identity(person, entity, lookup):
            accepted[person_id] = entity_id
            entity_of[person_id] = entity
        elif entity:
            rejected += 1
    print(f"身份校验通过 {len(accepted)} 位，排除同名冲突 {rejected} 位。", flush=True)

    # ---- 3. 导语抓取（维基百科不可达时跳过，综述仅用结构化事实） ----
    sitelinks: dict[str, str] = {}
    for person_id in accepted:
        title = entity_of[person_id].get("sitelinks", {}).get("zhwiki", {}).get("title")
        if title:
            sitelinks[person_id] = title
    extracts = wiki_extracts(sorted(set(sitelinks.values()))) if sitelinks and zh_channel else {}
    print(f"确认中文维基百科条目 {len(sitelinks)} 位，抓到导语 {len(extracts)} 篇。", flush=True)

    # ---- 4. 综述写库 ----
    written = 0
    verified_total = 0

    def lead_summary(person_id: str) -> str:
        """维基数据声明稀薄时的兜底：摘取条目导语前两句（来源随附，CC BY-SA）。"""

        extract = extracts.get(sitelinks.get(person_id, ""), "")
        sentences = [part for part in extract.replace("\n", " ").split("。") if part.strip()]
        return "。".join(sentences[:2]) + "。" if len(sentences) >= 2 else ""

    with connect() as db:
        for person in people:
            person_id = person["id"]
            entity_id = accepted.get(person_id)
            if not entity_id:
                continue
            entity = entity_of.get(person_id, {})
            digest = digested_facts(person, entity, lookup)
            current_bio = (person["biography"] or "").strip()
            is_stub = any(marker in current_bio for marker in STUB_MARKERS) or len(current_bio) < 60
            if is_stub and len(digest) >= 40:
                life = digest
                biography = digest
            elif is_stub and lead_summary(person_id):
                life = lead_summary(person_id)
                biography = life
            elif digest:
                life = f"{current_bio}\n\n{digest}"
                biography = current_bio
            else:
                life = current_bio
                biography = current_bio
            verified = "已校验" if "zhwiki" in entity.get("sitelinks", {}) else "未校验"
            db.execute(
                "UPDATE person SET biography = ?, verification_status = ? WHERE id = ?",
                (biography, verified, person_id),
            )
            if person_id not in sectioned and life:
                db.execute(
                    """
                    INSERT INTO person_section(person_id, section_key, title, position, content)
                    VALUES (?, 'life', '生平', 0, ?)
                    ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content
                    """,
                    (person_id, life),
                )
            reference_rows = [
                ("person", person_id, "life", 1, "中文维基百科检索", f"https://zh.wikipedia.org/wiki/{quote(person['name'])}", person["name"], "用于人工复核"),
            ]
            if person_id in sitelinks:
                reference_rows.insert(
                    0,
                    ("person", person_id, "life", 0, "中文维基百科条目", f"https://zh.wikipedia.org/wiki/{quote(sitelinks[person_id])}", sitelinks[person_id], "身份经维基数据匹配"),
                )
            db.executemany(
                """
                INSERT INTO content_reference(content_type, content_id, section_key, position, title, url, locator, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_type, content_id, section_key, position) DO UPDATE SET
                    title = excluded.title, url = excluded.url, locator = excluded.locator, note = excluded.note
                """,
                reference_rows,
            )
            status = "matched" if entity_id else "not_found"
            db.execute(
                """
                INSERT INTO person_research(person_id, provider, status, entity_id, checked_at, note)
                VALUES (?, 'wikipedia', ?, ?, ?, ?)
                ON CONFLICT(person_id, provider) DO UPDATE SET
                    status = excluded.status, entity_id = excluded.entity_id,
                    checked_at = excluded.checked_at, note = excluded.note
                """,
                (person_id, status, entity_id or "", datetime.now(timezone.utc).isoformat(timespec="seconds"), entity_id or "未找到精确匹配"),
            )
            written += 1
            if verified == "已校验":
                verified_total += 1

    with connect() as db:
        total_verified = db.execute("SELECT COUNT(*) FROM person WHERE verification_status = '已校验'").fetchone()[0]
    print(f"完成：写库 {written} 位；本轮标记已校验 {verified_total} 位；全库已校验 {total_verified} 位。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
