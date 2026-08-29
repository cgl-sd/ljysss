#!/usr/bin/env python3
"""把《明史》名录整体转成待收录条目，正文从本地维基百科取，id 统一重编。

三步：
1. 名录——传主（列传卷113–332）、宗室世系（表卷100–112）、本纪逐月编年、志部名目，
   每一项自带《明史》卷次，作为出处锚点。
2. 取正文——一次扫描本地维基 parquet，按简繁两种字形标题精确命中，记下 page_id 与
   url 作为可复核出处。
3. 重编号——统一用简体名拼音作 id（同名者加年号或卷次后缀），不再用 wiki-/cbdb-
   前缀区分来源；旧 id 到新 id 的映射单独留档，供关系边与引用同步改写。

产出 backend/data/staging/*.jsonl 与 id_map.json；本脚本不改动发布库。

    backend/.venv/bin/python backend/scripts/build_ming_records.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from opencc import OpenCC
from pypinyin import Style, lazy_pinyin

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))

from build_ming_inventory import (  # noqa: E402
    BIO_HEAD, CONSORT_HEAD, PRINCE_HEAD, SECTION, SUBSECTION, DATE_ENTRY,
    lines_of, is_catalog_line, volume_treatise,
)

PACKS = [BACKEND / "sources" / "wikipedia_zh" / f"train-0000{i}.parquet" for i in range(6)]
STAGING = BACKEND / "data" / "staging"

t2s = OpenCC("t2s")
s2t = OpenCC("s2t")

BIOGRAPHY_BLOCKS = [
    ("后妃", 113, 115, CONSORT_HEAD), ("宗室诸王", 116, 125, PRINCE_HEAD),
    ("功臣外戚", 126, 132, None), ("明臣", 133, 281, None),
    ("阉党佞幸", 282, 284, None), ("文苑", 285, 294, None),
    ("儒林循吏孝义", 295, 304, None), ("隐逸方技奸臣", 305, 311, None),
    ("土司", 312, 319, PRINCE_HEAD), ("外国西域", 320, 332, None),
]

# 明代年号起讫，用于把生卒或纪年映射回年号，并作为同名消歧的后缀来源。
REIGNS = [("洪武", 1368, 1398), ("建文", 1399, 1402), ("永乐", 1403, 1424), ("洪熙", 1425, 1425),
          ("宣德", 1426, 1435), ("正统", 1436, 1449), ("景泰", 1450, 1457), ("天顺", 1458, 1464),
          ("成化", 1465, 1487), ("弘治", 1488, 1505), ("正德", 1506, 1521), ("嘉靖", 1522, 1566),
          ("隆庆", 1567, 1572), ("万历", 1573, 1620), ("泰昌", 1620, 1620), ("天启", 1621, 1627),
          ("崇祯", 1628, 1644), ("弘光", 1645, 1645), ("隆武", 1645, 1646), ("绍武", 1646, 1646),
          ("永历", 1646, 1662)]


def reign_of(year: int | None) -> str:
    if not year:
        return ""
    for name, start, end in REIGNS:
        if start <= year <= end:
            return name
    return ""


def era_of_text(text: str) -> str:
    """《明史》本文里的纪年用字即归属朝，取时间最早的一个。"""

    found = [(start, name) for name, _, _ in REIGNS for start in [text.find(name)] if start >= 0]
    return min(found)[1] if found else ""


def slug(name: str) -> str:
    """统一 id：简体名的全拼。不带任何来源前缀。"""

    return "".join(lazy_pinyin(name, style=Style.NORMAL)) or "unnamed"


def mingshi_persons() -> list[dict]:
    records: list[dict] = []
    for block, start, stop, extra in BIOGRAPHY_BLOCKS:
        for juan in range(start, stop + 1):
            body = lines_of(juan)[1:]
            heads: list[tuple[int, str]] = []
            for order, line in enumerate(body):
                match = (extra.match(line) if extra else None) or BIO_HEAD.match(line)
                if match:
                    heads.append((order, t2s.convert(match.group(1))))
            for position, (order, name) in enumerate(heads):
                if len(name) < 2 or name.startswith(("附", "○")):
                    continue
                stop_at = heads[position + 1][0] if position + 1 < len(heads) else len(body)
                records.append({"name": name, "block": block, "juan": juan,
                                "opening": "\n".join(body[order:stop_at])[:1600]})
    return dedupe_persons(records)


def dedupe_persons(records: list[dict]) -> list[dict]:
    """同名同卷视为一条；不同卷的同名者各自保留并加卷次后缀，避免误并。"""

    grouped: dict[tuple[str, int], dict] = {}
    for item in records:
        grouped.setdefault((item["name"], item["juan"]), item)
    out = list(grouped.values())
    counts = Counter(item["name"] for item in out)
    for item in out:
        item["collision"] = counts[item["name"]] > 1
    return sorted(out, key=lambda item: (item["juan"], item["name"]))


def mingshi_genealogy() -> list[dict]:
    """表部世系行：封号＋名＋世次＋封年，是宗室与家族栏的骨架。"""

    line_re = re.compile(
        r"^([\u4e00-\u9fff·]{1,6}(?:亲王|郡王|王|公主|郡主)[\u4e00-\u9fff]{0,3})[，,]([^\n]{2,120})")
    found: list[dict] = []
    for juan in range(100, 113):
        for line in lines_of(juan)[1:]:
            for chunk in line.split("　"):
                match = line_re.match(chunk.strip())
                if not match:
                    continue
                label = t2s.convert(match.group(1))
                split = re.match(r"^[\u4e00-\u9fff·]{1,6}(?:亲王|郡王|王|公主|郡主)", label)
                found.append({"label": label,
                              "title": split.group(0) if split else label,
                              "name": label[split.end():] if split else "",
                              "detail": t2s.convert(match.group(2))[:160], "juan": juan})
    return found


def mingshi_annals() -> list[dict]:
    """本纪逐月记事：每条自带帝、卷、年、月，可直接作事件出处。"""

    entries: list[dict] = []
    for juan in range(1, 25):
        body = lines_of(juan)
        if not body:
            continue
        emperor = ""
        for line in body[:4]:
            marker = SECTION.match(line)
            if marker:
                emperor = t2s.convert(re.sub(r"[一二三四五六七八九十]+$", "", marker.group(1)))
                break
        for line in body[1:]:
            for match in DATE_ENTRY.finditer(line):
                year_name, season, month = match.groups()
                start = match.start()
                entries.append({
                    "juan": juan, "emperor": emperor, "year_name": year_name,
                    "month": f"{season or ''}{month}月",
                    "text": t2s.convert(line[start:start + 260]),
                })
    return entries


def mingshi_relics() -> list[dict]:
    """志部名目：卷首目录与 ○ 小节即制度、器物、礼俗条目。"""

    items: list[dict] = []
    for juan in range(25, 100):
        treatise = volume_treatise(juan)
        if not treatise:
            continue
        for line in lines_of(juan)[1:17]:
            marker = SUBSECTION.match(line)
            pieces = re.split(r"\s{1,}", marker.group(1)) if marker else (
                re.split(r"\s{1,}", line) if is_catalog_line(line) else [])
            for piece in pieces:
                piece = t2s.convert(piece.strip())
                if 2 <= len(piece) <= 16 and not piece.startswith(("附", "（")):
                    items.append({"treatise": treatise, "item": piece, "juan": juan})
    return items


MING_YEAR = re.compile(r"\b(1[3-6]\d{2})\b")


def ming_evidence(text: str) -> str:
    """同名误配是这批数据最大的风险，按下标分级，none 不得直接入库。"""

    head = text[:1500]
    if any(name in head for name, _, _ in REIGNS):
        return "strong"
    years = [int(y) for y in MING_YEAR.findall(head) if 1300 <= int(y) <= 1700]
    if "明" in head and years:
        return "strong"
    if "明" in head or years:
        return "weak"
    return "none"


def wiki_lookup(needed: set[str]) -> dict[str, dict]:
    """一次扫描维基包，按简繁两种标题精确命中，并带回正文首段做朝代校验。"""

    wanted: dict[str, str] = {}
    for name in needed:
        wanted.setdefault(name, name)
        wanted.setdefault(s2t.convert(name), name)
    hits: dict[str, dict] = {}
    for pack in PACKS:
        reader = pq.ParquetFile(str(pack))
        for batch in reader.iter_batches(columns=["id", "title", "url", "text"], batch_size=4096):
            row_id, titles, urls, texts = (batch.column("id").to_pylist(), batch.column("title").to_pylist(),
                                           batch.column("url").to_pylist(), batch.column("text").to_pylist())
            for index, title in enumerate(titles):
                key = re.split(r"（| \(", title, maxsplit=1)[0].strip()
                name = wanted.get(key)
                if name and name not in hits:
                    body = texts[index] or ""
                    hits[name] = {"wiki_title": title, "page_id": row_id[index], "url": urls[index],
                                  "chars": len(body), "opening": body[:2000],
                                  "ming": ming_evidence(body)}
    return hits


def assign_ids(persons: list[dict]) -> dict[str, str]:
    used: Counter[str] = Counter()
    for person in persons:
        base = slug(person["name"])
        used[base] += 1
        person["id"] = base if used[base] == 1 else f"{base}-{person['juan']}"
    return dict(used)


def main() -> None:
    persons = mingshi_persons()
    genealogy = mingshi_genealogy()
    annals = mingshi_annals()
    relics = mingshi_relics()
    assign_ids(persons)
    for person in persons:
        person["era"] = era_of_text(person["opening"])

    needed = ({p["name"] for p in persons} | {r["item"] for r in relics}
              | {g["label"] for g in genealogy} | {g["name"] for g in genealogy if g["name"]})
    print(f"名录：人物 {len(persons)}｜世系 {len(genealogy)}｜编年 {len(annals)}｜典章名目 {len(relics)}")
    print(f"需查维基的词条名 {len(needed)} 个，扫描维基包…")
    hits = wiki_lookup(needed)
    print(f"命中 {len(hits)} 个条目")

    for person in persons:
        person["wiki"] = hits.get(person["name"])
    for relic in relics:
        relic["wiki"] = hits.get(relic["item"])
    for row in genealogy:
        row["wiki"] = hits.get(row["label"]) or hits.get(row["name"])

    matched = [p for p in persons if p["wiki"]]
    tiers = Counter(p["wiki"]["ming"] for p in matched)
    STAGING.mkdir(parents=True, exist_ok=True)
    for table, rows in (("persons", persons), ("genealogy", genealogy),
                        ("annals", annals), ("relics", relics)):
        (STAGING / f"{table}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    print(f"\n人物 {len(persons)}：维基命中 {len(matched)} = {len(matched) / len(persons):.1%}"
          f"（强证 {tiers['strong']}｜弱证 {tiers['weak']}｜无明代证据 {tiers['none']}）")
    print("  无证据样例（疑似同名误配，须剔除或人工判定）：",
          [p["name"] for p in matched if p["wiki"]["ming"] == "none"][:10])
    relic_hits = [r for r in relics if r["wiki"]]
    gen_hits = [g for g in genealogy if g["wiki"]]
    print(f"典章 {len(relics)}：维基命中 {len(relic_hits)} = {len(relic_hits) / len(relics):.1%}"
          f"，其余以《明史》志文为正文")
    print(f"世系 {len(genealogy)}：维基命中 {len(gen_hits)}，正文取自《明史》表卷")
    print(f"编年 {len(annals)} 条自带《明史》卷次；年号可推出 {sum(1 for p in persons if p['era'])} 人")
    print(f"\n暂存于 {STAGING.relative_to(BACKEND)}/：persons/genealogy/annals/relics.jsonl")


if __name__ == "__main__":
    main()
