#!/usr/bin/env python3
"""从维基文库抓取《明史》全文并建立人物传文索引。

- --fetch：逐卷抓取明史/卷1..卷332，经 opencc 转为简体，存 sources/mingshi_full/（定形与缺卷补齐由 build_mingshi_full.py 负责）。
- --index：把 748 位人物匹配到列传（“某某，字……”起句）与本纪（庙号），
  选段写入 person_mingshi 表，并在“生平”栏目末尾追加〔《明史》原文〕块。

传文为 1739 年官修史书，属公版；选段上限 2000 字符，网文只有标题层，
不做逐字校勘，仅作导览加深。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from opencc import OpenCC  # noqa: E402

from app.database import connect, initialize_database  # noqa: E402

WIKISOURCE_API = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "LiangjingYishisanshengResearch/1.0 (historical educational app)"
TOTAL_JUANS = 332
CORPUS_DIRECTORY = BACKEND_DIRECTORY / "sources" / "mingshi_full"
EXCERPT_LIMIT = 2800
BIO_HEAD_PATTERN = re.compile(r"^([\u4e00-\u9fa5·]{2,4})，")
TEMPLE_NAMES = (
    "太祖", "惠帝", "成祖", "仁宗", "宣宗", "英宗", "景帝", "宪宗",
    "孝宗", "武宗", "世宗", "穆宗", "神宗", "光宗", "熹宗", "庄烈帝", "思宗",
)

cc = OpenCC("t2s")


def watched_urlopen(request, timeout: int = 25):
    """DNS 挂起无超时概念，统一用线程看门狗硬限。"""

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(urlopen, request, None, timeout)
        return future.result(timeout=timeout + 10)


TAGS = re.compile(r"<[^>]+>")
# 维基文库的模板文字，全部不是《明史》本文。
NOISE = (
    "公有领域", "维基文库", "免责声明", "永久链接", "页面权限", "本模版", "姊妹计划",
    "此作品已完成", "上传文件", "短链接", "跨语言链接", "在其他项目中", "检索自", "本页面",
)
BLOCK = re.compile(r"<(p|table)\b[^>]*>(.*?)</\1>", re.S)


def strip_tags(fragment: str) -> str:
    """去标签并折叠空白——古籍本文没有空格，维基模板塞进来的换行空白一律去掉。"""

    return re.sub(r"[\s\u3000]+", "", unescape(TAGS.sub("", fragment)))


def render_table(fragment: str) -> list[str]:
    """表格按行取单元格，行内用全角空格分隔，保持世系的横向阅读顺序。

    页顶页底的「上一卷 ◄ 明史卷N … ► 下一卷」导航框同样是表格，整张跳过。
    """

    if "◄" in fragment or "►" in fragment:
        return []
    noisy = lambda value: any(marker in value for marker in NOISE)
    lines = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", fragment, re.S):
        cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        line = "　".join(cell for cell in cells if cell and not noisy(cell))
        if line and not noisy(line):
            lines.append(line)
    return lines


def fetch_juan(juan: int) -> str:
    page = f"明史/卷{juan}"
    url = (
        f"{WIKISOURCE_API}?action=parse&page={quote(page)}&prop=text"
        f"&format=json&formatversion=2"
    )
    data = json.load(watched_urlopen(Request(url, headers={"User-Agent": USER_AGENT})))
    html = data.get("parse", {}).get("text", "")
    html = re.sub(r"<(style|script|sup)[^>]*>.*?</\1>", "", html, flags=re.S)

    lines: list[str] = []
    for kind, fragment in BLOCK.findall(html):
        if kind == "table":
            lines += render_table(fragment)
            continue
        text = strip_tags(fragment)
        if text and not any(marker in text for marker in NOISE):
            lines.append(text)
    return cc.convert("\n".join(lines))


def cmd_fetch(args) -> None:
    CORPUS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    def fetch_one(juan: int) -> tuple[int, str | None]:
        target = CORPUS_DIRECTORY / f"卷{juan:03d}.txt"
        if target.exists() and target.stat().st_size > 200:
            return juan, None
        for attempt in range(3):
            try:
                return juan, fetch_juan(juan)
            except Exception as error:
                if attempt == 2:
                    print(f"卷{juan}: 抓取失败（{error}）", flush=True)
                    return juan, None
                time.sleep(3 * (attempt + 1))
        return juan, None

    done = 0
    failed: list[int] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for juan, text in pool.map(fetch_one, range(1, TOTAL_JUANS + 1)):
            done += 1
            if text is not None:
                (CORPUS_DIRECTORY / f"卷{juan:03d}.txt").write_text(text, encoding="utf-8")
            if done % 40 == 0:
                print(f"已完成 {done}/{TOTAL_JUANS}", flush=True)
    failed = [juan for juan in range(1, TOTAL_JUANS + 1) if not (CORPUS_DIRECTORY / f"卷{juan:03d}.txt").exists()]
    print(f"抓取完成，失败 {len(failed)} 卷：{failed[:20]}", flush=True)


def load_catalog_people():
    with connect() as db:
        people = db.execute("SELECT id, name, title, years, reign FROM person ORDER BY id").fetchall()
        life_sections = {
            row["person_id"]: row["content"]
            for row in db.execute("SELECT person_id, content FROM person_section WHERE section_key = 'life'")
        }
        existing = {(r[0], r[1]) for r in db.execute("SELECT person_id, juan FROM person_mingshi")}
    return people, life_sections, existing


def split_biographies(paragraphs: list[str]) -> list[tuple[str, int]]:
    """列传按“某某，字/某”起句切分传主。"""

    heads = []
    for index, para in enumerate(paragraphs):
        m = BIO_HEAD_PATTERN.match(para)
        if m:
            heads.append((m.group(1), index))
    return heads


def excerpt_of(paragraphs: list[str], start: int, stop: int) -> str:
    chunk = "\n".join(paragraphs[start:stop])
    if len(chunk) > EXCERPT_LIMIT:
        chunk = chunk[:EXCERPT_LIMIT].rsplit("。", 1)[0] + "。"
    return chunk


def cmd_index(args) -> None:
    people, life_sections, existing = load_catalog_people()
    name_to_people: dict[str, list] = {}
    for person in people:
        name_to_people.setdefault(person["name"], []).append(person)
    given_to_people: dict[str, list] = {}
    for person in people:
        for given in (person["name"][1:], person["name"][2:]):
            if len(given) >= 2:
                given_to_people.setdefault(given, []).append(person)

    matches: dict[str, list[dict]] = {}
    juan_count = 0
    for juan in range(1, TOTAL_JUANS + 1):
        target = CORPUS_DIRECTORY / f"卷{juan:03d}.txt"
        if not target.exists():
            continue
        paragraphs = [p for p in target.read_text(encoding="utf-8").split("\n") if p.strip()]
        juan_count += 1
        kind = "本纪" if juan <= 24 else "列传"
        if kind == "列传":
            heads = split_biographies(paragraphs)
            full_matched = {person["name"] for name, _ in heads for person in name_to_people.get(name, [])}
            surnames_in_juan = {name[0] for name, _ in heads}
            for order, (name, para_index) in enumerate(heads):
                stop = heads[order + 1][1] if order + 1 < len(heads) else len(paragraphs)
                for person in name_to_people.get(name, []):
                    matches.setdefault(person["id"], []).append(
                        {"juan": juan, "kind": kind, "excerpt": excerpt_of(paragraphs, para_index, stop)}
                    )
                # 单名附传：起句用名（“辉祖，”），需同卷存在同姓传主佐证，且全局唯一
                candidates = given_to_people.get(name, [])
                if len(candidates) == 1 and candidates[0]["name"][0] in surnames_in_juan and candidates[0]["name"] not in full_matched:
                    matches.setdefault(candidates[0]["id"], []).append(
                        {"juan": juan, "kind": kind, "excerpt": excerpt_of(paragraphs, para_index, stop)}
                    )
        else:
            # 本纪归属：以卷首句所冠庙号为准（如“太祖开天行道……”“成祖启弘……”），
            # 只在帝王（title 以“明”开头的本朝君主）中匹配，避免被功臣头衔“明太祖封”劫持。
            first_para = paragraphs[0] if paragraphs else ""
            head_text = "\n".join(paragraphs[:6])
            emperors = [p for p in people if p["title"].startswith("明")]
            chosen = None
            for temple in TEMPLE_NAMES:
                if first_para.startswith(temple) or temple in first_para[:16]:
                    chosen = temple
                    break
            if chosen is None:
                for temple in TEMPLE_NAMES:
                    if temple in head_text:
                        chosen = temple
                        break
            if chosen:
                for person in emperors:
                    if chosen in person["title"]:
                        matches.setdefault(person["id"], []).append(
                            {"juan": juan, "kind": kind, "excerpt": excerpt_of(paragraphs, 0, min(10, len(paragraphs)))}
                        )
                        break
    print(f"语料 {juan_count} 卷；命中人物 {len(matches)} 位。", flush=True)

    # 附传提取：无选段而父/兄弟已有传文者，在父卷原文中按“名，”起句定位。
    with connect() as db:
        thin_people = {
            row["id"]: row
            for row in db.execute(
                """
                SELECT p.id, p.name FROM person p
                LEFT JOIN person_section ps ON ps.person_id = p.id AND ps.section_key = 'life'
                WHERE ps.content IS NULL OR (ps.content NOT LIKE '%《明史》原文%' AND length(ps.content) < 500)
                """
            )
        }
        kin = db.execute(
            """
            SELECT pr.from_person_id, pr.to_person_id, pr.relation_type FROM person_relation pr
            JOIN person_mingshi pm ON pm.person_id IN (pr.from_person_id, pr.to_person_id)
            WHERE pr.relation_type IN ('父子', '兄弟姐妹')
            """
        ).fetchall()
        mingshi_juan = {row["person_id"]: row["juan"] for row in db.execute("SELECT person_id, juan FROM person_mingshi")}
        person_names = {row["id"]: row["name"] for row in db.execute("SELECT id, name FROM person")}
    attach_found = 0
    for row in kin:
        a, b, rel = row["from_person_id"], row["to_person_id"], row["relation_type"]
        target = b if a in thin_people else (a if b in thin_people else None)
        anchor_person = a if target == b else b
        if target not in thin_people or anchor_person not in mingshi_juan:
            continue
        person = thin_people[target]
        given = person["name"][1:]
        if len(given) < 1 or person["id"] in matches:
            continue
        juan = mingshi_juan[anchor_person]
        target_path = CORPUS_DIRECTORY / f"卷{juan:03d}.txt"
        if not target_path.exists():
            continue
        paragraphs = [p for p in target_path.read_text(encoding="utf-8").split("\n") if p.strip()]
        # 定位父/兄传主的首段，再在其后的段落中找以“名”开头的附传
        anchor_head = 0
        for order, para in enumerate(paragraphs):
            if para.startswith(anchor_person_name + "，") or para.startswith(anchor_person_name):
                anchor_head = order
                break
        for order in range(anchor_head + 1, len(paragraphs)):
            para = paragraphs[order]
            if para.startswith(given) and not split_biographies([para]):
                stop = len(paragraphs)
                for later in range(order + 1, len(paragraphs)):
                    if split_biographies([paragraphs[later]]):
                        stop = later
                        break
                matches.setdefault(person["id"], []).append(
                    {"juan": juan, "kind": "列传", "excerpt": excerpt_of(paragraphs, order, stop)}
                )
                attach_found += 1
                break
    print(f"附传提取 {attach_found} 位。", flush=True)

    appended = 0
    with connect() as db:
        for person_id, entries in matches.items():
            for entry in entries:
                key = (person_id, entry["juan"])
                if key in existing:
                    continue
                db.execute(
                    "INSERT OR REPLACE INTO person_mingshi(person_id, juan, kind, excerpt) VALUES (?, ?, ?, ?)",
                    (person_id, entry["juan"], entry["kind"], entry["excerpt"]),
                )
            primary = entries[0]
            marker = "〔《明史》原文〕"
            current = life_sections.get(person_id)
            if current and marker not in current:
                db.execute(
                    "UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'life'",
                    (f"{current}\n\n{marker}\n{primary['excerpt']}", person_id),
                )
                appended += 1
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM person_mingshi").fetchone()[0]
    print(f"索引完成：传文索引 {total} 条；生平追加原文 {appended} 位。", flush=True)


def quote(value: str) -> str:
    from urllib.parse import quote as urlquote

    return urlquote(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取并索引《明史》全文")
    parser.add_argument("--phase", choices=["fetch", "index", "all"], default="all")
    parser.add_argument("--sleep", type=float, default=0.45)
    args = parser.parse_args()

    initialize_database()
    if args.phase in ("fetch", "all"):
        cmd_fetch(args)
    if args.phase in ("index", "all"):
        cmd_index(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
