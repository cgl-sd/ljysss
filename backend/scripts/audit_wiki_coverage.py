#!/usr/bin/env python3
"""维基明代相关内容覆盖面审计：以《明史》自名录为独立尺子，量出我们漏了多少。

收录脚本此前的候选池是「《明史》传首 2–4 字姓名 ∩ 维基标题完全同名」，事件与典章
则全靠一份 51 + 27 项的手工术语表，尺子被人为限死，所以只做出 76 个事件。本脚本
改用多条互相独立的轴同时扫描，并按软件里的类别（人物 / 事件 / 典章名物）分别报告
已收录与缺失，供后续逐期收敛。

    .venv/bin/python scripts/audit_wiki_coverage.py

只读：不写内容库，只输出报告与缺失清单到 stdout / /tmp/wiki_coverage_gap_*.json。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pyarrow.parquet as pq
from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
MINGSHI = BACKEND / "sources" / "mingshi"
PACKS = [BACKEND / "sources" / "wikipedia_zh" / f"train-0000{i}.parquet" for i in range(6)]
STORE = BACKEND / "data" / "ming_history.sqlite3"

s2t = OpenCC("s2t")
t2s = OpenCC("t2s")

# 传主名录：明史每卷首行是以空格分隔的该卷全部传主（含附传），比传首正则全。
TOC_NAME = re.compile(r"^[\u4e00-\u9fff·]{2,7}$")
CLIP = re.compile(r"[〈（].*?[〉）]")
# 传首正文形如「庞尚鹏，字少南，南海人。」「某某，安陆人。」——要求带籍贯或「字」，
# 否则「一日，」这类句首会被误判成人名。
BIO_STRICT = re.compile(r"^([\u4e00-\u9fff·]{2,5})，(?:[^。\n]{0,12}字[^。\n]{1,10}|[^。\n]{0,20}?(?:人|籍[^。\n]{1,10}))。")

# 年号全集（含南明与追尊），用于标题法与朝代校核轴。
ERAS = [
    "洪武", "建文", "永乐", "洪熙", "宣德", "正统", "景泰", "天顺", "成化", "弘治", "正德",
    "嘉靖", "隆庆", "万历", "泰昌", "天启", "崇祯", "南明", "弘光", "隆武", "绍武", "永历",
    "洪化", "顺天", "奉天",
]
MING_TITLE = re.compile(r"^(明朝|明代|明初|明末|南明)|(" + "|".join(ERAS) + r")")
# 事件法：不靠手工术语表，改用通名后缀。
EVENT_TITLE = re.compile(r"(之役|之变|之乱|之案|案$|起义|兵变|之役|北伐|东征|西征|亲征|迁都|封贡|开关|党案|国争|战争|之战)")
# 典章名物法：以志部通名与「制/度/司/监/院/府/卫/券/剑/印/服/器/钱/钞/赋/法/学/仓/库」收尾。
RELIC_TITLE = re.compile(r"(制度|官制|兵制|税制|田制|科举|服饰|舆服|器用|宝玺|印信|钱币|货币|仓储|驿传|盐法|茶法|漕运|河渠|历法|乐律|礼制|祭祀|陵寝|宫阙|苑囿|城垣|军器|火器|造船|陶瓷|织造|医药|算学|历算$)")


def mingshi_heads() -> tuple[set[str], dict[str, int]]:
    """返回（简化的传主名集合, 名字→卷次）。"""
    names: dict[str, int] = {}
    for path in sorted(MINGSHI.glob("卷*.txt")):
        juan = int(path.stem[1:])
        if not 113 <= juan <= 299:      # 300 卷起为土司/外国传，记政权不记明人
            continue
        text = path.read_text(encoding="utf-8")
        paras = [p for p in text.split("\n") if p.strip()]
        if not paras:
            continue
        for part in re.split(r"[\s　]+", CLIP.sub("", paras[0])):
            if TOC_NAME.match(part):
                names.setdefault(t2s.convert(part), juan)
        for para in paras[1:]:
            m = BIO_STRICT.match(para)
            if m:
                names.setdefault(t2s.convert(m.group(1)), juan)
    return set(names), names


def main() -> None:
    head_s, head_juan = mingshi_heads()
    # 「一元」「九年」这类数量词句首会被传首正则误收，先从尺子里剔掉。
    numeral = re.compile(r"^[一二三四五六七八九十百千零]+[元年的日]?")
    head_s = {n for n in head_s if not numeral.match(n) and n not in set(ERAS)}
    head_t = {s2t.convert(n) for n in head_s}
    head_lookup = head_s | head_t
    print(f"《明史》列传(卷113–299)传主名录: {len(head_s)} 名（含目次附传，已剔数量词假名）")

    import sqlite3

    store = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    have_titles = {r[0] for r in store.execute("select id from person where id like 'wiki-%'")}
    have_names = {t2s.convert(r[0]) for r in store.execute("select name from person")}
    event_rows = [r[0] for r in store.execute("select title from event")]
    relic_rows = [t2s.convert(r[0]) for r in store.execute("select name from special_item")]
    have_events = {t2s.convert(t) for t in event_rows}
    have_relics = set(relic_rows)
    print(f"库内: person {len(have_names)}（wiki 来源 {len(have_titles)}）"
          f"｜event {len(event_rows)} 行 / {len(have_events)} 个不同标题"
          f"｜special_item {len(relic_rows)} 行 / {len(have_relics)} 个不同名")
    dup = sorted({t for t in event_rows if event_rows.count(t) > 1})
    dupr = sorted({t for t in relic_rows if relic_rows.count(t) > 1})
    if dup or dupr:
        print(f"  重名（需消歧或合并）: 事件 {dup}｜典章 {dupr}")
    print()

    matched_heads: dict[str, str] = {}
    era_titles: list[str] = []
    event_titles: list[str] = []
    relic_titles: list[str] = []
    total = 0
    for pack in PACKS:
        table = pq.read_table(str(pack), columns=["title"])
        for title in table.column("title").to_pylist():
            total += 1
            base = re.split(r" \(|（", title, maxsplit=1)[0]
            s = t2s.convert(base)
            if s in head_s or base in head_lookup:
                matched_heads.setdefault(s, title)
            ming = bool(MING_TITLE.search(title))
            if ming:
                era_titles.append(title)
            if ming and EVENT_TITLE.search(base):
                event_titles.append(title)
            if ming and RELIC_TITLE.search(base):
                relic_titles.append(title)
    print(f"维基全量条目 {total}")

    missing_heads = sorted(set(matched_heads) - have_names)
    print(f"\n【人物】明史传主 ∩ 维基有条目: {len(matched_heads)}")
    print(f"  已收录 {len(matched_heads) - len(missing_heads)} ｜ 缺失 {len(missing_heads)}"
          f" ｜ 缺失率 {len(missing_heads) / max(len(matched_heads), 1):.1%}")
    print(f"  缺失样例: {missing_heads[:25]}")

    print(f"\n【事件】标题含明代年号/明朝 且带事件通名: {len(event_titles)}")
    ev_missing = [t for t in event_titles if t2s.convert(re.split(r' \(|（', t, 1)[0]) not in
                  {t2s.convert(e) for e in have_events}]
    print(f"  库内现有 {len(have_events)} 条，标题法可见但未收录: {len(ev_missing)}")
    print(f"  样例: {ev_missing[:18]}")

    print(f"\n【典章名物】标题含制度/器物通名: {len(relic_titles)}")
    rl = sorted({t2s.convert(re.split(r' \(|（', t, 1)[0]) for t in relic_titles})
    rl_missing = [t for t in rl if t not in have_relics and not any(t in h or h in t for h in have_relics)]
    print(f"  库内 {len(have_relics)} 条，标题法可见但未收录: {len(rl_missing)}")
    print(f"  样例: {rl_missing[:18]}")

    prefix = sorted({t2s.convert(t) for t in era_titles})
    print(f"\n【总盘子】标题命中明代年号/明朝/南明的条目共 {len(prefix)} 条（含各语言/列表页）")

    # 反向校核：库内人物的明代证据强度，为零证据者列出待删名单。
    era_set = set(ERAS[:17])
    strong = dated = zero = 0
    zero_list: list[str] = []
    for pid, name, reign, years in store.execute("select id, name, reign, years from person"):
        s = t2s.convert(name)
        if s in head_s:
            strong += 1
            continue
        by = re.match(r"^(\d{4})—(\d{4})$", years)
        if any(e in reign for e in era_set) and by and 1300 <= int(by.group(1)) <= 1660:
            dated += 1
        else:
            zero += 1
            zero_list.append(f"{name}|{reign}|{years}")
    print(f"\n【反向校核】库内 2200 人的明代证据强度")
    print(f"  在《明史》传主名录内      {strong}")
    print(f"  名录外但年号+生卒均可证    {dated}")
    print(f"  两者皆无（零证据，待逐个过目）{zero}")
    print(f"  零证据样例: {zero_list[:15]}")

    Path("/tmp/wiki_coverage_gap_persons.json").write_text(
        json.dumps({"missing": missing_heads,
                    "juan": {n: head_juan.get(n) for n in missing_heads},
                    "matched": len(matched_heads)}, ensure_ascii=False, indent=1), encoding="utf-8")
    Path("/tmp/wiki_coverage_gap_events.json").write_text(
        json.dumps(sorted(set(ev_missing)), ensure_ascii=False, indent=1), encoding="utf-8")
    Path("/tmp/wiki_coverage_gap_relics.json").write_text(
        json.dumps(rl_missing, ensure_ascii=False, indent=1), encoding="utf-8")
    Path("/tmp/wiki_zero_evidence_persons.json").write_text(
        json.dumps(sorted(zero_list), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n缺失清单已写到 /tmp/wiki_coverage_gap_{persons,events,relics}.json"
          " 与 /tmp/wiki_zero_evidence_persons.json")


if __name__ == "__main__":
    main()
