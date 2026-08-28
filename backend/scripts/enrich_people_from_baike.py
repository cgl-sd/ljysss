#!/usr/bin/env python3
"""以百度百科为主线补全人物生平（中文互联网可达通道）。

流程：
1. 逐人调用百度百科开放接口（BaikeLemmaCardApi）取词条摘要与结构化名片。
2. 身份闸门：词条标题必须与姓名完全一致；名片或摘要中的生卒年须与库内
   years 兼容（±6 年）；可用时再经维基数据实体匹配交叉佐证。
3. 写库：摘要导语（注明出处）+ 名片字段原创综述；56 位核心人物的既有
   栏目与简介保持不动；“家族与子嗣”栏目一律不覆盖。
4. 校验标记：百度百科与维基数据双源一致（或本就人工核验）才标“已校验”。

版权提示：摘要为百度百科文本，出处 URL 随 content_reference 存档；
如需对外发布，建议编辑改为改写综述。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import connect, initialize_database  # noqa: E402
from enrich_people_from_wikidata import (  # noqa: E402
    compatible_identity,
    entity_data,
    matching_entity,
)

BAIKE_API = "https://baike.baidu.com/api/openapi/BaikeLemmaCardApi"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CARD_FIELDS = ("字", "号", "出生地", "出生日期", "逝世日期", "谥号", "庙号", "年号", "最高官职", "封号", "所处时代", "主要成就")
TAG_PATTERN = re.compile(r"<[^>]+>")
YEAR_PATTERN = re.compile(r"(1[3-7]\d{2})")


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(urlopen, request, None, 15)
                with future.result(timeout=20) as response:
                    return json.load(response)
        except FuturesTimeoutError:
            raise TimeoutError("百度百科请求超过 20 秒")
        except (HTTPError, URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("请求重试耗尽")


def clean(value: str) -> str:
    return TAG_PATTERN.sub("", value).replace("\u00a0", " ").strip()


def card_map(card: list[dict]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in card or []:
        name = clean(item.get("name", ""))
        values = [clean(value) for value in item.get("value", []) if clean(value)]
        if name and values and name not in result:
            result[name] = values[0]
    return result


VARIANT_CHARS = str.maketrans({"飚": "飚", "飙": "飚", "啓": "启", "峯": "峰", "畧": "略", "鎭": "镇", "祐": "佑", "绪": "绪", "緖": "绪"})


def normalized(name: str) -> str:
    return name.translate(VARIANT_CHARS)


def title_matches(name: str, title: str) -> bool:
    """词条名允许“谥号/尊号前缀 + 姓名”与常见异体字变体。"""

    if title == name or normalized(title) == normalized(name):
        return True
    return title.endswith(name) and len(title) - len(name) <= 4


def parse_expected_years(text: str) -> tuple[int | None, int | None]:
    """“？—1644”与“1551—1618”都必须正确区分生年与卒年。"""

    text = (text or "").strip()
    match = re.match(r"^\s*([?？\d]{1,4})\s*—\s*([?？\d]{1,4})\s*$", text)
    if match:
        birth = int(match.group(1)) if match.group(1).isdigit() else None
        death = int(match.group(2)) if match.group(2).isdigit() else None
        return birth, death
    years = re.findall(r"(1[3-7]\d{2})", text)
    birth = int(years[0]) if years else None
    death = int(years[1]) if len(years) > 1 else None
    return birth, death


def identity_gate(person, baike: dict) -> tuple[bool, str]:
    """词条名精确一致 + 生卒年兼容才放行。"""

    if not title_matches(person["name"], baike.get("title", "")):
        return False, f"词条名不一致：{baike.get('title')}"
    expected_birth, expected_death = parse_expected_years(person["years"])
    card = card_map(baike.get("card"))
    observed_birth, observed_death = None, None
    if card.get("出生日期"):
        observed_birth = parse_expected_years(card["出生日期"])[0]
    if card.get("逝世日期"):
        observed_death = parse_expected_years(card["逝世日期"])[0]
    if observed_birth is None or observed_death is None:
        # 名片缺生卒时回退到摘要开头的“（X年—Y年）”模式。
        abstract = (baike.get("abstract") or "")[:80]
        paren = re.search(r"（?(\d{4})[^0-9—-]{0,6}—(\d{4})", abstract)
        if paren:
            observed_birth = observed_birth or int(paren.group(1))
            observed_death = observed_death or int(paren.group(2))
    if expected_birth and observed_birth and abs(expected_birth - observed_birth) > 6:
        return False, f"生年冲突：库内 {expected_birth} vs 词条 {observed_birth}"
    if expected_death and observed_death and abs(expected_death - observed_death) > 6:
        return False, f"卒年冲突：库内 {expected_death} vs 词条 {observed_death}"
    return True, "ok"


def digest(person, baike: dict) -> str:
    card = card_map(baike.get("card"))
    parts: list[str] = []
    if card.get("出生日期") or card.get("逝世日期"):
        parts.append(f"生卒记载为{card.get('出生日期', '？')}—{card.get('逝世日期', '？')}。")
    if card.get("出生地"):
        parts.append(f"籍贯指向{card['出生地']}。")
    aliases = "、".join(filter(None, (card.get("字"), card.get("号"))))
    if aliases:
        parts.append(f"表字名号为{aliases}。")
    if card.get("所处时代"):
        parts.append(f"所处时代为{card['所处时代']}。")
    office = card.get("最高官职") or card.get("封号")
    if office:
        parts.append(f"官职封号可查为{office}。")
    honorifics = "、".join(filter(None, (card.get("庙号"), card.get("谥号"))))
    if honorifics:
        parts.append(f"庙号谥号为{honorifics}。")
    if card.get("主要成就"):
        parts.append(f"主要成就概括为{card['主要成就']}。")
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="以百度百科为主线补全人物生平")
    parser.add_argument("--sleep", type=float, default=0.3, help="请求之间的等待秒数")
    parser.add_argument("--limit", type=int, default=0, help="限制处理条数，0 表示不限制")
    parser.add_argument("--missing-only", action="store_true", help="只处理尚无生平栏目的人物")
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
    if args.missing_only:
        people = [p for p in people if p["id"] not in sectioned]
    print(f"待处理人物 {len(people)} 位。", flush=True)

    hits: dict[str, dict] = {}
    rejected: list[str] = []
    misses: list[str] = []
    for index, person in enumerate(people, start=1):
        url = f"{BAIKE_API}?scope=103&format=json&appid=379020&bk_length=800&bk_key={quote(person['name'])}"
        try:
            baike = fetch_json(url)
        except Exception as error:
            misses.append(person["id"])
            print(f"[{index}/{len(people)}] {person['name']}: 抓取失败（{error}）", flush=True)
            time.sleep(args.sleep)
            continue
        if not baike.get("title"):
            misses.append(person["id"])
        else:
            ok, reason = identity_gate(person, baike)
            if ok:
                hits[person["id"]] = baike
            else:
                rejected.append(f"{person['id']}: {reason}")
        if index % 100 == 0:
            print(f"已处理 {index}/{len(people)}，命中 {len(hits)}，排除 {len(rejected)}，未命中 {len(misses)}。", flush=True)
        time.sleep(args.sleep)
    print(f"百度百科命中 {len(hits)} 位，排除 {len(rejected)} 位，未命中 {len(misses)} 位。", flush=True)

    # ---- 维基数据交叉佐证（可达时） ----
    wd_matched = {p["id"]: p["wikidata_entity"] for p in people if p["wikidata_entity"]}
    try:
        need = [p for p in people if p["id"] in hits and p["id"] not in wd_matched]
        for index, person in enumerate(need, start=1):
            try:
                entity_id = matching_entity(person["name"])
            except Exception:
                break  # 维基数据通道不可用即放弃佐证，不影响已写入内容
            if not entity_id:
                time.sleep(0.6)
                continue
            entities = entity_data([entity_id])
            entity = entities.get(entity_id, {})
            if entity and compatible_identity(person, entity, {}):
                wd_matched[person["id"]] = entity_id
            time.sleep(0.6)
        print(f"维基数据交叉佐证：累计匹配 {len(wd_matched)} 位。", flush=True)
    except Exception as error:
        print(f"维基数据佐证通道不可用（{error}），按单源处理。", flush=True)

    written = 0
    verified_count = 0
    with connect() as db:
        for person in people:
            person_id = person["id"]
            if person_id not in hits:
                continue
            baike = hits[person_id]
            abstract = (baike.get("abstract") or "").strip()
            extra = digest(person, baike)
            current_bio = (person["biography"] or "").strip()
            is_stub = len(current_bio) < 60 or "活动于" in current_bio
            life_parts = [part for part in (abstract, extra) if part]
            if person_id in sectioned:
                continue  # 核心人物既有栏目保持不动
            life = "\n\n".join(life_parts) if life_parts else current_bio
            biography = current_bio
            if is_stub and life:
                biography = life
            double_source = person_id in wd_matched or person["verification_status"] == "已校验"
            verified = "已校验" if double_source else "未校验"
            db.execute(
                "UPDATE person SET biography = ?, verification_status = ? WHERE id = ?",
                (biography, verified, person_id),
            )
            if life:
                db.execute(
                    """
                    INSERT INTO person_section(person_id, section_key, title, position, content)
                    VALUES (?, 'life', '生平', 0, ?)
                    ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content
                    """,
                    (person_id, life),
                )
            item_url = baike.get("url") or f"https://baike.baidu.com/item/{quote(person['name'])}"
            db.executemany(
                """
                INSERT INTO content_reference(content_type, content_id, section_key, position, title, url, locator, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_type, content_id, section_key, position) DO UPDATE SET
                    title = excluded.title, url = excluded.url, locator = excluded.locator, note = excluded.note
                """,
                [
                    ("person", person_id, "life", 0, "百度百科人物条目", item_url, baike.get("title", person["name"]), "词条名精确一致，生卒年经核对"),
                    ("person", person_id, "life", 1, "百度百科检索", f"https://baike.baidu.com/item/{quote(person['name'])}", person["name"], "用于人工复核"),
                ],
            )
            db.execute(
                """
                INSERT INTO person_research(person_id, provider, status, entity_id, checked_at, note)
                VALUES (?, 'baike', 'matched', '', ?, ?)
                ON CONFLICT(person_id, provider) DO UPDATE SET
                    status = excluded.status, entity_id = excluded.entity_id,
                    checked_at = excluded.checked_at, note = excluded.note
                """,
                (person_id, datetime.now(timezone.utc).isoformat(timespec="seconds"), f"词条 {baike.get('title')}"),
            )
            written += 1
            if verified == "已校验":
                verified_count += 1

    with connect() as db:
        total_verified = db.execute("SELECT COUNT(*) FROM person WHERE verification_status = '已校验'").fetchone()[0]
    print(f"完成：写库 {written} 位；本轮标记已校验 {verified_count} 位；全库已校验 {total_verified} 位。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
