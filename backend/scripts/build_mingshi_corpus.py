#!/usr/bin/env python3
"""从维基文库抓取《明史》全文并建立人物传文索引。

- --fetch：逐卷抓取明史/卷1..卷332，经 opencc 转为简体，存 data/mingshi/。
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
CORPUS_DIRECTORY = BACKEND_DIRECTORY / "data" / "mingshi"
EXCERPT_LIMIT = 2000
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


def fetch_juan(juan: int) -> str:
    page = f"明史/卷{juan}"
    url = (
        f"{WIKISOURCE_API}?action=parse&page={quote(page)}&prop=text"
        f"&format=json&formatversion=2"
    )
    data = json.load(watched_urlopen(Request(url, headers={"User-Agent": USER_AGENT})))
    html = data.get("parse", {}).get("text", "")
    body = re.sub(r"<(style|table|sup)[^>]*>.*?</\1>", "", html, flags=re.S)
    paragraphs = [
        re.sub(r"<[^>]+>", "", p).strip()
        for p in re.findall(r"<p>(.*?)</p>", body, flags=re.S)
    ]
    paragraphs = [cc.convert(p) for p in paragraphs if p]
    return "\n".join(paragraphs)


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
            for order, (name, para_index) in enumerate(heads):
                for person in name_to_people.get(name, []):
                    stop = heads[order + 1][1] if order + 1 < len(heads) else len(paragraphs)
                    matches.setdefault(person["id"], []).append(
                        {"juan": juan, "kind": kind, "excerpt": excerpt_of(paragraphs, para_index, stop)}
                    )
        else:
            head_text = "\n".join(paragraphs[:6])
            for temple in TEMPLE_NAMES:
                if temple in head_text:
                    for person in people:
                        if temple in person["title"]:
                            matches.setdefault(person["id"], []).append(
                                {"juan": juan, "kind": kind, "excerpt": excerpt_of(paragraphs, 0, min(8, len(paragraphs)))}
                            )
                            break
                    break
    print(f"语料 {juan_count} 卷；命中人物 {len(matches)} 位。", flush=True)

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
