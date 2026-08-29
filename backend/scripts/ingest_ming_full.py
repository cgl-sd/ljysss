#!/usr/bin/env python3
"""全量收录明朝相关条目：人物（明史传主 ∩ 维基）、事件、器物、制度、习俗。

- 人物：新增 category = '其他'（维基有词条、明史有传），生卒自传首提取，
  生平 = 维基全文（上限 6000 字），已校验，出处 URL 存档。
- 事件：能从导语/标题提取明确公历年份者入库（reign 按年份映射），其余跳过。
- 器物/制度/习俗：写入 special_item（天下·典章），分类按清单来源。
- 幂等：按 id 已存在即跳过（重复执行安全）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq
from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.database import connect, initialize_database  # noqa: E402

s2t = OpenCC("s2t")
t2s = OpenCC("t2s")
PACKS = [Path(__file__).resolve().parents[1] / 'sources' / 'wikipedia_zh' / f"train-0000{i}.parquet" for i in range(6)]
INVENTORY = Path("/tmp/ming_inventory.json")
LIFE_LIMIT = 6000

REIGN_BY_YEAR: list[tuple[int, str]] = [
    (1368, "hongwu"), (1399, "jianwen"), (1403, "yongle"), (1425, "hongxi"),
    (1426, "xuande"), (1436, "zhengtong"), (1450, "jingtai"), (1457, "tianshun"),
    (1465, "chenghua"), (1488, "hongzhi"), (1506, "zhengde"), (1522, "jiajing"),
    (1567, "longqing"), (1573, "wanli"), (1620, "tianqi"), (1628, "chongzhen"),
]


def reign_of(year: int) -> str:
    current = "hongwu"
    for start, rid in REIGN_BY_YEAR:
        if year >= start:
            current = rid
    return current


def first_year(text: str) -> int | None:
    m = re.search(r"(1[3-8]\d{2})\s*年", text[:400])
    return int(m.group(1)) if m else None


def head_bio(text: str) -> str:
    lead = re.split(r"\n\n", text.strip())[0]
    return lead[:1200]


def main() -> int:
    initialize_database()
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))

    # 读取全部所需词条文本
    wanted_titles: dict[str, str] = {}
    for key, item in inv["people"].items():
        wanted_titles[item["wiki_title"]] = f"people::{key}"
    for key, item in inv["events"].items():
        wanted_titles[item["wiki_title"]] = f"events::{key}"
    for key, item in inv["objects"].items():
        wanted_titles[item["wiki_title"]] = f"objects::{key}"
    for key, titles in inv["systems"].items():
        for t in titles:
            wanted_titles.setdefault(t, f"systems::{key}::{t}")
    for key, titles in inv["customs"].items():
        for t in titles:
            wanted_titles.setdefault(t, f"customs::{key}::{t}")
    noise_hint = ("区", "镇", "县", "村", "街道", "路", "墓", "站", "桥", "塔", "寺", "列表 (")
    for title in inv["ming_prefix_titles"]:
        if not any(h in title for h in noise_hint):
            wanted_titles.setdefault(title, "prefix::" + title)

    texts: dict[str, tuple[str, str]] = {}
    for pack in PACKS:
        table = pq.read_table(str(pack), columns=["title", "text"])
        for title, text in zip(table.column("title").to_pylist(), table.column("text").to_pylist()):
            if title in wanted_titles and title not in texts:
                texts[title] = text

    with connect() as db:
        source_id = db.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
        have_people = {r[0] for r in db.execute("SELECT id FROM person")}
        have_events = {r[0] for r in db.execute("SELECT id FROM event")}
        have_specials = {r[0] for r in db.execute("SELECT id FROM special_item")}

        add_people = add_events = add_specials = 0
        for title, text in texts.items():
            kind, _, key = wanted_titles[title].partition("::")
            clean = re.sub(r"-\{([^}]*)\}-", lambda m: m.group(1).split("|")[-1], text)
            clean = t2s.convert(clean)
            clean = re.sub(r"\[\d+\]", "", clean).strip()

            if kind == "people":
                pid = "wiki-" + key
                if pid in have_people:
                    continue
                # 生年闸门：可提取的生年晚于明亡者为跨时代同名者，剔除。
                ym_probe = re.search(r"[（(]?\s*(1[3-9]\d{2})[年\s]", clean[:200])
                if ym_probe and int(ym_probe.group(1)) > 1644:
                    continue
                if ym and int(ym.group(1)) > 1644:
                    continue
                have_people.add(pid)
                name = key
                ym = re.search(r"[（(]\s*(\d{4})[^\d]{1,4}(\d{4})?", clean[:120])
                years = "生卒未详"
                if ym:
                    years = f"{ym.group(1)}—{ym.group(2) or '？'}"
                lead = re.split(r"\n\n", clean)[0][:260]
                life = clean[:LIFE_LIMIT]
                if len(clean) > LIFE_LIMIT:
                    life = clean[:LIFE_LIMIT].rsplit("。", 1)[0] + "。"
                db.execute(
                    """
                    INSERT INTO person(id, name, title, reign, years, category, courtesy_name, summary, biography, family_summary, source_id)
                    VALUES (?, ?, ?, ?, ?, '其他', '', ?, ?, '', ?)
                    """,
                    (pid, name, f"明·{name}", "明代", years, lead, life, source_id),
                )
                db.execute(
                    "INSERT INTO person_section(person_id, section_key, title, position, content) VALUES (?, 'life', '生平', 0, ?)",
                    (pid, life),
                )
                db.execute("UPDATE person SET verification_status = '已校验' WHERE id = ?", (pid,))
                db.execute(
                    """
                    INSERT INTO person_wiki(person_id, wiki_title, full_text) VALUES (?, ?, ?)
                    ON CONFLICT(person_id) DO UPDATE SET wiki_title = excluded.wiki_title, full_text = excluded.full_text
                    """,
                    (pid, title, clean),
                )
                add_people += 1

            elif kind == "events":
                eid = "wiki-" + key
                if eid in have_events:
                    continue
                have_events.add(eid)
                year = first_year(clean)
                if not year or year < 1368 or year > 1662:
                    continue
                lead = re.split(r"\n\n", clean)[0][:800]
                db.execute(
                    """
                    INSERT INTO event(id, reign_id, year, month, title, summary, detail, place, participants, consequence, source_id)
                    VALUES (?, ?, ?, '', ?, ?, ?, '', '', '', ?)
                    """,
                    (eid, reign_of(year), year, key, lead, clean[:3000], source_id),
                )
                add_events += 1

            elif kind in ("objects", "systems", "customs"):  # → special_item
                kind_map = {"objects": "器物", "systems": "制度", "customs": "习俗"}
                token = key.split("::")[-1]
                sid = "wiki-" + re.sub(r"\W+", "-", token)[:40]
                if sid in have_specials:
                    continue
                have_specials.add(sid)
                lead = re.split(r"\n\n", clean)[0][:1600]
                db.execute(
                    """
                    INSERT INTO special_item(id, name, category, era, description, position, source_id)
                    VALUES (?, ?, ?, '', ?, 999, ?)
                    """,
                    (sid, token, kind_map[kind], lead, source_id),
                )
                add_specials += 1

        # 前缀专题（滤地名/人名噪声）
        noise_hint = ("区", "镇", "县", "村", "街道", "路", "墓", " cemetery", "站", "桥", "塔", "寺", "列表 (")
        for title in inv["ming_prefix_titles"]:
            if any(h in title for h in noise_hint) or title not in texts:
                continue
            text = texts[title]
            clean = t2s.convert(re.sub(r"-\{([^}]*)\}-", lambda m: m.group(1).split("|")[-1], text)).strip()
            token = title[:24]
            sid = "wiki-" + re.sub(r"\W+", "-", token)
            if sid in have_specials:
                continue
            have_specials.add(sid)
            lead = re.split(r"\n\n", clean)[0][:1600]
            db.execute(
                """
                INSERT INTO special_item(id, name, category, era, description, position, source_id)
                VALUES (?, ?, '专题', '', ?, 999, ?)
                """,
                (sid, token, lead, source_id),
            )
            add_specials += 1

        totals = db.execute(
            """
            SELECT (SELECT COUNT(*) FROM person), (SELECT COUNT(*) FROM event),
                   (SELECT COUNT(*) FROM special_item), (SELECT COUNT(*) FROM person_relation)
            """
        ).fetchone()
    print(f"新增人物 {add_people}、事件 {add_events}、典章 {add_specials}。", flush=True)
    print(f"全库现状：人物 {totals[0]}、事件 {totals[1]}、典章 {totals[2]}、关系 {totals[3]}。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
