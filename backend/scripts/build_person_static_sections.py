#!/usr/bin/env python3
"""把维基可查那批人物的介绍整理成库内数据。

范围只含在维基有对应条目的人（content_reference 带 url）；其余人物本轮不动。

四块内容各归各位，都是可与生平同级查询的数据，不是预先拼好的展示文字：

- 生平  person_section(section_key='life')      维基条目正文为主，附《明史》本传原文块
- 亲属  person_kin                              CBDB 亲属记录（带出处）＋《明史》本传中的父子兄弟句；
                                                对方已在库内则记 kin_person_id，界面可直接跳转
- 关系  person_relation                         同僚、统属、君臣、配偶、兄弟姐妹等
- 事件  event ＋ event_participant              本纪逐月编年入库，参与人以 person_id 关联

正文已被判为挂错人（同名他人）的，生平一律用《明史》本文，不再回退到维基。
人工校订过的家族栏（≥80 字）保持不动。

    backend/.venv/bin/python backend/scripts/build_person_static_sections.py --dry-run
    backend/.venv/bin/python backend/scripts/build_person_static_sections.py
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
CONTENT = BACKEND / "data" / "content"
STAGING = BACKEND / "data" / "staging"
CBDB = BACKEND / "sources" / "cbdb" / "cbdb_20260822.sqlite3"

t2s = OpenCC("t2s")

TABLES = ["person", "person_section", "person_relation", "person_kin", "event",
          "event_participant", "annal", "annal_participant",
          "content_reference", "person_wiki", "person_mingshi", "person_cbdb"]

MANUAL_FAMILY_FLOOR = 80
WIKI_NOISE = re.compile(r"^(?:==+[^=]+==+|\{\{[^}]*\}\}|参考資料|外部連結|外部链接|注釋|注释|參見|参见|维基|Wiki).*$")
KIN_PHRASE = re.compile(r"[，。；](父|母|妻|妃|子|男|弟|兄|女)([\u4e00-\u9fff]{1,6})[，。；]")
CLOSE_KIN = re.compile(r"父|母|妻|夫|子|女|兄|弟|姊|妹|祖|孫|孙")
REGNAL = re.compile(r"^(至正|洪武|建文|永樂|永乐|洪熙|宣德|正統|正统|景泰|天順|天顺|成化|弘治|正德|嘉靖|隆慶|隆庆|萬曆|万历|泰昌|天啟|天启|崇禎|崇祯|弘光|隆武|紹武|绍武|永曆|永历)(元|[一二三四五六七八九十]{1,3})年")
CN = {"元": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
REIGN_START = {"洪武": 1368, "建文": 1399, "永乐": 1403, "洪熙": 1425, "宣德": 1426, "正统": 1436,
               "景泰": 1450, "天顺": 1458, "成化": 1465, "弘治": 1488, "正德": 1506, "嘉靖": 1522,
               "隆庆": 1567, "万历": 1573, "泰昌": 1620, "天启": 1621, "崇祯": 1628, "弘光": 1645,
               "隆武": 1645, "绍武": 1646, "永历": 1646, "至正": 1341}


def load(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(table: str, rows: list[dict]) -> None:
    (CONTENT / f"{table}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


# 本纪各帝对应的年号；卷内承前纪年（「十五年春正月」）不重复写年号，靠这张表补算
EMPEROR_REIGN = {"太祖": "洪武", "恭闵帝": "建文", "成祖": "永乐", "仁宗": "洪熙", "宣宗": "宣德",
                 "英宗前纪": "正统", "英宗后纪": "天顺", "宪宗": "成化", "孝宗": "弘治", "武宗": "正德",
                 "世宗": "嘉靖", "穆宗": "隆庆", "神宗": "万历", "光宗": "泰昌", "熹宗": "天启",
                 "庄烈帝": "崇祯", "景帝": "景泰", "代宗": "景泰"}


def numeral_year(text: str) -> int:
    """把「洪武三年」「十五年」里的纪年数字转成公元年；缺年号时返回 0。"""

    match = REGNAL.match(text or "")
    if not match:
        bare = re.match(r"^([一二三四五六七八九十]{1,3})年", text or "")
        if not bare:
            return 0
        return CN_OF(bare.group(1))
    return CN_OF(match.group(2))


def CN_OF(numeral: str) -> int:
    if numeral == "元":
        return 1
    if numeral.startswith("十"):
        return 10 + (CN.get(numeral[1:], 0) if len(numeral) > 1 else 0)
    if numeral.endswith("十"):
        return CN.get(numeral[0], 1) * 10
    if "十" in numeral:
        head, tail = numeral.split("十", 1)
        return CN.get(head, 1) * 10 + CN.get(tail, 0)
    return CN.get(numeral, 0)


def regnal_year(text: str, emperor: str = "") -> int:
    offset = numeral_year(text)
    if not offset:
        return 0
    match = REGNAL.match(text or "")
    reign = t2s.convert(match.group(1)) if match else EMPEROR_REIGN.get(emperor, "")
    start = REIGN_START.get(reign, 0)
    return start + offset - 1 if start else 0


def clean_wiki(text: str) -> str:
    lines = []
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line or WIKI_NOISE.match(line) or line.startswith(("!", "#", "*", ":", ";", "==")):
            continue
        line = t2s.convert(re.sub(r"\[\d+\]|\[[a-z]\]|\{\{[^}]*\}\}|<[^>]+>", "", line)).strip()
        if len(line) >= 8:
            lines.append(line)
    return "\n".join(lines)


def cbdb_kin() -> dict[int, list[tuple[str, str, str]]]:
    """CBDB 亲属：本人 cbdb_id → [(关系, 亲属 CBDB 编号, 亲属姓名)]。"""

    if not CBDB.exists():
        return {}
    out: dict[int, list[tuple[str, str, str]]] = defaultdict(list)
    with sqlite3.connect(f"file:{CBDB}?mode=ro", uri=True) as link:
        rows = link.execute(
            """
            SELECT k.c_personid, kc.c_kinrel_chn, k.c_kin_id, b.c_name_chn
            FROM KIN_DATA k
            JOIN KINSHIP_CODES kc ON kc.c_kincode = k.c_kin_code
            LEFT JOIN BIOG_MAIN b ON b.c_personid = k.c_kin_id
            """).fetchall()
    for person_id, relation, kin_id, kin_name in rows:
        relation, kin_name = t2s.convert(relation or ""), t2s.convert(kin_name or "")
        if not relation or not kin_name or "未詳" in relation or "missing" in relation:
            continue
        if not CLOSE_KIN.search(relation):
            continue
        out[person_id].append((relation, str(kin_id), kin_name))
    return out


def compose_articles(targets, tables, lives_by_person, manual_family) -> None:
    """把亲属、关系、事件三块各写成一篇叙述文字，与生平同质地存进 person_section。"""

    by_id = {p["id"]: p for p in tables["person"]}
    kin_by_person: dict[str, list[dict]] = defaultdict(list)
    for row in tables["person_kin"]:
        kin_by_person[row["person_id"]].append(row)
    edges_by_person: dict[str, list[dict]] = defaultdict(list)
    for edge in tables["person_relation"]:
        for a, b in ((edge["from_person_id"], edge["to_person_id"]), (edge["to_person_id"], edge["from_person_id"])):
            edges_by_person[a].append({"other": b, "type": edge["relation_type"], "note": edge.get("note", "")})
    events_by_person: dict[str, list[dict]] = defaultdict(list)
    for link in tables["event_participant"]:
        event = next((e for e in tables["event"] if e["id"] == link["event_id"]), None)
        if event:
            events_by_person[link["person_id"]].append(
                {"year": event.get("year"), "label": event.get("title", ""),
                 "body": (event.get("summary") or "")[:90], "cite": "《明史》事件专条"})
    # 编年条目同样进「相关事件」文章——它给的是系年事实，与专条互补
    annals = {a["id"]: a for a in tables.get("annal", [])}
    for link in tables.get("annal_participant", []):
        annal = annals.get(link["annal_id"])
        if annal:
            events_by_person[link["person_id"]].append(
                {"year": annal.get("year"),
                 "label": re.sub(r"^([元一二三四五六七八九十]{1,3}年|永樂|永乐)(春|夏|秋|冬)?", "",
                                 annal["text"]).split("。")[0][:40] or annal["text"][:40],
                 "body": annal["text"], "cite": f"《明史》本纪卷{annal['juan']}"})

    GROUP = {"父": "父", "母": "母", "妻": "配偶", "妃": "配偶", "夫": "配偶",
             "子": "子", "男": "子", "女": "女", "兄": "兄", "弟": "弟"}

    for person in targets:
        pid = person["id"]

        kin = kin_by_person.get(pid, [])
        if kin:
            grouped: dict[str, list[str]] = defaultdict(list)
            for row in kin:
                grouped[GROUP.get(row["relation"], row["relation"])].append(row["kin_name"])
            sentences = []
            for label in ("父", "母", "配偶", "子", "女", "兄", "弟"):
                names = list(dict.fromkeys(grouped.get(label, [])))
                if not names:
                    continue
                if label in ("子", "女"):
                    sentences.append(f"{label} {len(names)} 人：{'、'.join(names[:12])}。")
                else:
                    sentences.append(f"{label}{'、'.join(names[:4])}。")
            manual = manual_family.get(pid, "")
            article = "".join(sentences)
            if manual and manual not in ("其家世与亲属，现存史料未见详载。",):
                article = f"{article}\n\n{manual}" if article else manual
            if article.strip():
                lives_by_person[(pid, "family")] = ("家族", 1, article.strip())

        edges = [e for e in edges_by_person.get(pid, [])
                 if e["type"] not in ("父子", "母子") and e["other"] in by_id]
        if edges and person.get("category") != "帝王":
            lines = []
            for edge in edges[:14]:
                other = by_id[edge["other"]]["name"]
                lines.append(f"与{other}为{edge['type']}" + (f"，{edge['note']}" if edge["note"] else "。")
                             .rstrip("。") + "。")
            lives_by_person[(pid, "relations")] = ("人物关系", 2, "".join(lines))

        events = sorted(events_by_person.get(pid, []), key=lambda e: (e.get("year") or 9999, e["label"]))
        if events:
            lines = []
            for event in events[:18]:
                year = event.get("year")
                lines.append(f"{year or '年份待考'}年，{event['label'].rstrip('。，')}。（{event['cite']}）")
            lives_by_person[(pid, "events")] = ("相关事件", 3, "\n".join(lines))


def main(dry_run: bool) -> None:
    tables = {name: load(name) for name in TABLES}
    people = tables["person"]
    by_id = {p["id"]: p for p in people}
    name_to_id: dict[str, str] = {}
    for person in people:
        name_to_id.setdefault(person["name"], person["id"])

    wiki_of = {r["content_id"]: r["url"] for r in tables["content_reference"]
               if r.get("content_type") == "person" and r.get("url")}
    rejected = {r["content_id"] for r in tables["content_reference"]
                if "正文改用《明史》本文" in (r.get("note") or "")}
    targets = [p for p in people if p["id"] in wiki_of]
    print(f"库内 {len(people)} 人，本轮整理维基可查的 {len(targets)} 人"
          f"（其中 {len([p for p in targets if p['id'] in rejected])} 人正文已判挂错人，只用明史）")

    mingshi = {r["person_id"]: r["excerpt"] for r in tables["person_mingshi"]}
    roster_opening = {}
    for line in (STAGING / "persons.jsonl").read_text(encoding="utf-8").splitlines() if (STAGING / "persons.jsonl").exists() else []:
        entry = json.loads(line)
        roster_opening.setdefault(t2s.convert(entry["name"]), entry["opening"])
    existing_life = {r["person_id"]: r["content"] for r in tables["person_section"] if r["section_key"] == "life"}
    manual_family = {r["person_id"]: r["content"] for r in tables["person_section"] if r["section_key"] == "family"}
    kin_source = cbdb_kin()
    cbdb_of = {r["person_id"]: r["cbdb_id"] for r in tables["person_cbdb"]}
    cbdb_to_person: dict[str, str] = {}
    for person in people:
        cid = cbdb_of.get(person["id"])
        if cid is not None:
            cbdb_to_person.setdefault(str(cid), person["id"])

    stats: Counter[str] = Counter()
    articles: dict[tuple[str, str], tuple[str, int, str]] = {}
    kin_rows: dict[tuple[str, str, str], dict] = {}

    for person in targets:
        pid, name = person["id"], person["name"]
        excerpt = mingshi.get(pid) or roster_opening.get(name, "")

        # 生平：维基正文为主，明史本传原文附后；正文挂错人的只用明史
        if pid in rejected:
            body = ""
        else:
            wiki_row = next((r for r in tables["person_wiki"] if r["person_id"] == pid), None)
            body = clean_wiki(wiki_row["full_text"]) if wiki_row else ""
        if not body:
            body = existing_life.get(pid, "") or person.get("biography", "")
        if excerpt:
            body = f"{body}\n\n〔《明史》原文〕\n{excerpt[:900]}"
        if body.strip():
            articles[(pid, "life")] = ("生平", 0, body.strip())
            stats["生平"] += 1

        # 亲属：CBDB（带出处，对方在库内则可直接跳转）＋《明史》本传亲属句
        added_kin: list[tuple[str, str, str, str]] = []
        for relation, kin_cbdb_id, kin_name in kin_source.get(cbdb_of.get(pid, -1), [])[:14]:
            added_kin.append((relation, kin_name, cbdb_to_person.get(kin_cbdb_id, ""), "哈佛 CBDB 亲属记录"))
        source_text = excerpt or person.get("biography", "")
        for match in KIN_PHRASE.finditer(source_text[:900]):
            relation, kin_name = match.group(1), match.group(2)
            if 2 <= len(kin_name) <= 4 and not kin_name.startswith(("某", "氏")):
                added_kin.append((relation, kin_name, name_to_id.get(kin_name, ""), "《明史》本传"))
        for relation, kin_name, kin_pid, source in added_kin:
            key = (pid, kin_name, relation)
            if kin_name == name or key in kin_rows:
                continue
            kin_rows[key] = {"person_id": pid, "kin_person_id": kin_pid or None, "kin_name": kin_name,
                             "relation": relation, "note": "", "source": source}
            stats["亲属记录"] += 1
            if kin_pid:
                stats["亲属可跳转"] += 1

    # 事件：本纪逐月编年入库，参与人以 person_id 关联
    known_names = sorted((n for n in name_to_id if len(n) >= 2), key=len, reverse=True)
    annals_path = STAGING / "annals.jsonl"
    entries = [json.loads(line) for line in annals_path.read_text(encoding="utf-8").splitlines() if line.strip()] \
        if annals_path.exists() else []
    existing_event_ids = {e["id"] for e in tables["event"]}
    # event.reign_id 是外键，只能填 reign 表里的 id；按年份反查落在哪个年号
    spans = [(r["id"], r["start_year"], r["end_year"]) for r in load("reign")]

    def reign_id(year: int) -> str:
        for rid, start, end in spans:
            if start <= year <= end:
                return rid
        return "hongwu" if year and year < 1368 else (spans[-1][0] if spans else "hongwu")

    participants_of: dict[str, list[str]] = defaultdict(list)
    for index, entry in enumerate(entries):
        text = entry.get("text", "")
        year = regnal_year(entry.get("year_name", ""), entry.get("emperor", ""))
        heading = re.sub(r"^([元一二三四五六七八九十]{1,3}年)(春|夏|秋|冬)?", "",
                         re.sub(r"\s+", "", text)).split("。")[0][:34].rstrip("。，、")
        if not heading:
            continue
        event_id = f"mingshi-bj{entry['juan']:02d}-{index:03d}"
        if event_id in existing_event_ids:
            continue
        hits = [n for n in known_names if n in text]
        people_ids = sorted({name_to_id[n] for n in hits})[:12]
        tables["annal"].append({
            "id": event_id, "juan": entry["juan"], "emperor": entry.get("emperor", ""),
            "reign_id": reign_id(year), "year": year,
            "month": entry.get("month", ""), "text": text[:400],
        })
        for person_id in people_ids:
            participants_of[event_id].append(person_id)
    stats["编年条目"] = len(tables["annal"])
    # 参与人已解析到 person_id 的编年，同步登记关联
    for annal_id, people_ids in participants_of.items():
        for person_id in people_ids:
            tables["annal_participant"].append({"annal_id": annal_id, "person_id": person_id})
    # 精选事件的参与人也补进关联表，供文章与后续图表同源使用
    for event in tables["event"]:
        for name in [n for n in (event.get("participants") or "").split("、") if n.strip()]:
            person_id = name_to_id.get(name.strip())
            if person_id and not any(r["event_id"] == event["id"] and r["person_id"] == person_id
                                     for r in tables["event_participant"]):
                tables["event_participant"].append({"event_id": event["id"], "person_id": person_id,
                                                    "role": "参与"})
    stats["事件参与人"] = len(tables["event_participant"])

    # 关系边：亲属里双方都在库内的，补成 person_relation（父子/母子按既有约定）
    existing_edges = {(e["from_person_id"], e["to_person_id"], e["relation_type"], e.get("reign", ""))
                      for e in tables["person_relation"]}
    RELATION_TYPE = {"父": "父子", "母": "母子", "妻": "配偶", "妃": "配偶", "兄": "兄弟姐妹", "弟": "兄弟姐妹", "女": "母子"}
    source_id = tables["person"][0].get("source_id", "mingshi-editorial-v1")
    for row in kin_rows.values():
        child, parent = row["kin_person_id"], row["person_id"]
        if not child:
            continue
        edge_type = RELATION_TYPE.get(row["relation"])
        if not edge_type:
            continue
        father_side = row["relation"] in ("父", "母")
        first, second = (parent, child) if father_side else (child, parent)
        reign = by_id[row["person_id"]].get("reign", "")
        key = (first, second, edge_type, reign)
        if key in existing_edges:
            continue
        tables["person_relation"].append({"from_person_id": first, "to_person_id": second,
                                          "relation_type": edge_type, "reign": reign,
                                          "note": f"据{row['source']}", "source_id": source_id})
        existing_edges.add(key)
        stats["关系边新增"] += 1

    # 文章：亲属、关系、事件各成一篇，与生平同样存进 person_section
    compose_articles(targets, tables, articles, manual_family)

    # 写回：本轮目标人物的栏目整体替换，其余保留
    replaced = {(r["person_id"], r["section_key"]) for r in tables["person_section"]
                if (r["person_id"], r["section_key"]) in articles}
    kept = [r for r in tables["person_section"] if (r["person_id"], r["section_key"]) not in replaced]
    for (pid, key), (title, position, content) in articles.items():
        kept.append({"person_id": pid, "section_key": key, "title": title, "position": position, "content": content})
    tables["person_section"] = kept
    tables["person_kin"] = sorted(kin_rows.values(), key=lambda r: (r["person_id"], r["relation"], r["kin_name"]))

    print("\n" + "｜".join(f"{k} {v:,}" for k, v in stats.items()))
    kept_manual = sum(1 for person in targets
                       if len(manual_family.get(person['id'], '')) >= MANUAL_FAMILY_FLOOR)
    print(f"家族栏保留人工校订 {kept_manual} 人；文章栏目 {len(articles)} 篇")
    if dry_run:
        print("\n[dry-run] 未写入。")
        return
    for name, rows in tables.items():
        dump(name, rows)
    print("已写入 data/content/*.jsonl")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    main(parser.parse_args().dry_run)
