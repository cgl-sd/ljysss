#!/usr/bin/env python3
"""从本地中文维基数据包重建首版事件、机构和典章内容。

事件选择清单是本轮人工筛查后的固定输入；脚本不访问网络，也不改写人物表。
运行：
    backend/.venv/bin/python backend/scripts/rebuild_wiki_catalog.py --dry-run
    backend/.venv/bin/python backend/scripts/rebuild_wiki_catalog.py

正文来源只进入 JSONL 的内容字段。source_id 继续作为内部编辑追踪字段，阅读端不会显示。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from opencc import OpenCC
from pypinyin import Style, lazy_pinyin

BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"
PACKS = sorted((BACKEND / "sources" / "wikipedia_zh").glob("train-*.parquet"))

t2s = OpenCC("t2s")

# 这份名单对应本地候选池经首轮逐条筛查后的 161 个可发布条目。
EVENT_TITLES = """
1488年韦朝威起义
京师保卫战
京畿之戰
俺答封贡
凤阳之战
劉六劉七起義
南京教案
南北榜案
博洛平福建之战
吳橋兵變
土木堡之变
壬午之役
大同之战
大同兵變
宝庆之战
宣大之戰
寧夏之役
寧波之亂
寧王之亂
寧遠兵變
左安门之战
己巳之變 (崇禎)
庚戌之变
播州之役
新会之战
明-锡兰山国战争
明成祖远征漠北之战
明朝开国战争
明末襄阳之战
明灭夏之战
明缅战争
明英战争
朱高煦之亂
李自成攻开封之战
李自成攻朱仙鎮之戰
東林黨爭
楚太子案
楚宗劫槓案
楚藩宮變
永乐迁都
清灭南明之战
滿倉兒案
潮州之役
澎湖之战
王二起義
移宮案
第一次妖書案
第二次京畿之戰
第二次妖書案
紅丸案
茜草灣戰役
蓝山起义
薩爾滸之戰
遵永大捷
鄭成功攻臺之役
隆庆开关
靖难之役
魏觀案
麓川之役
丁亥之役
万全右卫之战
亮马佃大捷
保宁之战
停溪大捷
兀良哈之戰
兆佳城之战
刀干孟之乱
努尔哈赤统一建州女真之战
南渡三案
南都太子案
厦门战役 (1660年)
叙州大捷
古勒山之战
叶赫城之战
同安之役
壬寅宮變
大員之役
大悲案
大禮議
奢安之亂
孙可望、李定国收复湖南战役
宁锦之战
安化王之乱
定海关战役
小盈岭战役
崇武戰役
崒洞祝洞之戰
平壤之战 (1593年)
广渠门之战
应州大捷
开读之变
开铁之战
徐达北伐
护国岭战役
撫清之戰
支棱昌江之戰
明太祖第一次北伐
明太祖第七次北伐
明太祖第三次北伐
明太祖第二次北伐
明太祖第五次北伐
明太祖第八次北伐
明太祖第四次北伐
明平云南之战
明平闽广之战
明攻取河北之战
明攻山东之战
明攻山西之战
明攻河南之战
明朝午門血案
明朝苗族叛乱
明甲辰科场案
明麓战争 (1386年—1388年)
曲靖之战
李定国、白文选攻缅甸之战
松錦之戰
林宽起义
柳河之役
桂林大捷
梃擊案
江東橋戰役
沙定洲之亂
泉州戰役
泗川之戰
浑河之战 (1621年)
海澄战役
瓜州戰役
真定之戰
睢州之变
碧蹄館之戰
磁灶戰役
空印案
童妃案
红盐池之战
联明抗清
聯寇抗清
肇庆之役
胡惟庸案
胪朐河之战
茅麓山战役
萬曆朝鮮之役
藍玉案
衡阳大捷
西海之战
覺華島之戰
辰州大捷
郑旺妖言案
郭桓案
鄭成功北伐
重庆之役
金川門之變
钱山战役
银总起义
镇北关之战
镇江之战 (1621年)
青州之变
靖州大捷
鱼吕之乱
黄山案
黄道周北伐
黑河墩之战
""".splitlines()
if any(not line.strip() for line in EVENT_TITLES):
    EVENT_TITLES = [line.strip() for line in EVENT_TITLES if line.strip()]

ERAS = [
    ("洪武", 1368, 1398, "hongwu"), ("建文", 1399, 1402, "jianwen"),
    ("永乐", 1403, 1424, "yongle"), ("洪熙", 1425, 1425, "hongxi"),
    ("宣德", 1426, 1435, "xuande"), ("正统", 1436, 1449, "zhengtong"),
    ("景泰", 1450, 1457, "jingtai"), ("天顺", 1457, 1464, "tianshun"),
    ("成化", 1465, 1487, "chenghua"), ("弘治", 1488, 1505, "hongzhi"),
    ("正德", 1506, 1521, "zhengde"), ("嘉靖", 1522, 1566, "jiajing"),
    ("隆庆", 1567, 1572, "longqing"), ("万历", 1573, 1620, "wanli"),
    ("泰昌", 1620, 1620, "taichang"), ("天启", 1621, 1627, "tianqi"),
    ("崇祯", 1628, 1644, "chongzhen"), ("弘光", 1645, 1645, "nanming"),
    ("隆武", 1645, 1646, "nanming"), ("绍武", 1646, 1646, "nanming"),
    ("永历", 1646, 1662, "nanming"),
]
ERA_YEAR = {name: (start, rid) for name, start, _end, rid in ERAS}

NOISE_HEADINGS = {
    "参考文献", "参考资料", "注释", "脚注", "外部链接", "相关条目", "参见", "分类", "参考",
}
WIKI_MARKUP = re.compile(r"\[\d+\]|\{\{.*?\}\}|<[^>]+>|-\{([^{}]*)\}-")
YEAR_RE = re.compile(r"(?<!\d)(1[3-6]\d{2})\s*年")
MONTH_RE = re.compile(r"((?:正|闰)?[一二三四五六七八九十冬腊臘]+月|1[0-2]|[1-9])月")


def clean_line(text: str) -> str:
    text = WIKI_MARKUP.sub(lambda m: (m.group(1) or ""), text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"（\s*）|\(\s*\)", "", text)
    text = re.sub(r"[ \t\u3000]+", " ", text).strip()
    # 模板残留和单独标点没有阅读价值。
    if not text or re.fullmatch(r"[\W_·、，。；：！？（）()【】「」《》…—-]+", text):
        return ""
    return text


def clean_article(raw: str) -> tuple[str, list[tuple[str, str]]]:
    """返回正文与（标题，正文）分组；参考资料之后的内容全部丢弃。"""
    lines = [clean_line(t2s.convert(line)) for line in (raw or "").splitlines()]
    lines = [line for line in lines if line]
    groups: list[tuple[str, str]] = []
    current_title = "概览"
    current: list[str] = []
    for line in lines:
        if line in NOISE_HEADINGS or any(line.startswith(x) for x in NOISE_HEADINGS):
            break
        # 维基抓取文本的自然标题通常独占一行；过长句子不能误作标题。
        if len(line) <= 24 and not re.search(r"[。！？；：]", line) and (
            line in {"背景", "经过", "过程", "结果", "结局", "影响", "历史", "起因", "始末", "战役经过", "事件经过"}
            or (len(line) <= 12 and not YEAR_RE.search(line) and not re.search(r"[，、]", line))
        ):
            if current:
                groups.append((current_title, "\n".join(current)))
            current_title = line
            current = []
        else:
            current.append(line)
    if current:
        groups.append((current_title, "\n".join(current)))
    if not groups:
        groups = [("概览", clean_line(t2s.convert(raw)))]
    # 删除标题下重复的单独英文、脚注和过短噪声段。
    groups = [(title, body.strip()) for title, body in groups if len(body.strip()) >= 12]
    body = "\n\n".join((f"{title}\n{content}" if title != "概览" else content) for title, content in groups)
    return body[:30000], groups


def intro_text(raw: str) -> str:
    paragraphs = [clean_line(t2s.convert(p)) for p in re.split(r"\n\s*\n", raw or "")]
    paragraphs = [p for p in paragraphs if p]
    return paragraphs[0] if paragraphs else ""


def year_info(text: str) -> tuple[int, int, str]:
    probe = text[:2400]
    years = [int(v) for v in YEAR_RE.findall(probe)]
    if not years:
        for era, (start, _rid) in ERA_YEAR.items():
            if era in probe:
                years = [start]
                break
    if not years:
        return 0, 0, ""
    year = years[0]
    end = year
    range_match = re.search(rf"{year}\s*年[^。；\n]{{0,30}}?(?:至|到|—|-|～)\s*(1[3-6]\d{{2}})\s*年", probe)
    if range_match:
        end = int(range_match.group(1))
    month = MONTH_RE.search(probe)
    if not month:
        return year, end, "全年"
    # MONTH_RE 的数字分支只捕获数字，统一把月份写成读者可直接理解的“5月”，
    # 同时避免“五月月”这类重复后缀。
    month_value = month.group(1)
    return year, end, month_value if month_value.endswith("月") else f"{month_value}月"


def reign_id(year: int) -> str:
    # 1644 年明廷覆亡后进入南明阶段；南明在阅读端按时间顺序合并展示，
    # 不再拆分弘光、隆武、绍武、永历四个短年号。
    if year >= 1644:
        return "nanming"
    for _name, start, end, rid in ERAS:
        if start <= year <= end:
            return rid
    # 1367 年起的开国连续战事归入洪武档案。
    return "hongwu"


def classify(title: str, intro: str) -> str:
    if any(token in title for token in ("起义", "起義", "叛乱", "叛亂", "兵变", "兵變", "民变", "民變")):
        return "社会与民变"
    if any(token in title for token in ("迁都", "遷都", "封贡", "封貢", "开关", "開關")):
        return "外交与朝贡"
    if any(token in title for token in ("案", "之变", "之變", "之乱", "之亂", "党争", "黨爭", "教案")):
        return "宫廷政争"
    if any(token in title for token in ("战", "戰", "役", "战争", "戰爭", "大捷", "北伐", "远征", "遠征", "围城", "圍城")):
        return "战争与边防"
    if "明清战争" in title:
        return "战争与边防"
    return "建制与法令"


def place_from_intro(intro: str) -> str:
    patterns = [
        r"发生于([^，。；]{2,24})",
        r"發生於([^，。；]{2,24})",
        r"在([^，。；]{2,24})(?:进行|進行|爆发|爆發|发生|發生)",
    ]
    for pattern in patterns:
        m = re.search(pattern, intro)
        if m:
            value = re.sub(r"[（(].*?[）)]", "", m.group(1)).strip()
            if value:
                return value[:40]
    return ""


def slug(title: str, year: int, used: set[str]) -> str:
    base = "".join(lazy_pinyin(title, style=Style.NORMAL)) or "event"
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:48]
    value = f"wiki-event-{base}-{year or 'undated'}"
    suffix = 2
    while value in used:
        value = f"wiki-event-{base}-{year or 'undated'}-{suffix}"
        suffix += 1
    used.add(value)
    return value


def load_wiki() -> dict[str, str]:
    result: dict[str, str] = {}
    for pack in PACKS:
        table = pq.read_table(str(pack), columns=["title", "text"])
        for title, text in zip(table.column("title").to_pylist(), table.column("text").to_pylist()):
            if title not in result:
                result[title] = text or ""
    return result


def load_jsonl(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_jsonl(table: str, rows: list[dict]) -> None:
    path = CONTENT / f"{table}.jsonl"
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def ensure_wiki_source() -> None:
    """登记本地维基快照，使所有新增内容的 source_id 具备外键目标。"""
    rows = load_jsonl("source")
    if any(row.get("id") == "wikipedia-zh-20231101" for row in rows):
        return
    rows.append({
        "id": "wikipedia-zh-20231101",
        "title": "中文维基百科本地数据包（2023-11-01快照）",
        "citation": "项目内置中文维基百科 Parquet 数据包；仅用于编辑校验和内容重建。",
        "url": "",
        "review_status": "编辑依据",
    })
    dump_jsonl("source", rows)


def refresh_event_references(events: list[dict]) -> None:
    """替换旧事件的编辑来源索引，避免 content_reference 留下孤立 event_id。"""
    rows = [row for row in load_jsonl("content_reference") if row.get("content_type") != "event"]
    rows.extend({
        "content_type": "event",
        "content_id": event["id"],
        "section_key": "source",
        "position": 0,
        "title": "中文维基百科本地数据包",
        "url": "",
        "locator": f"维基条目：{event['title']}",
        "note": "用于编辑校验；阅读端不展示来源提示。",
    } for event in events)
    dump_jsonl("content_reference", rows)


def people_index() -> tuple[dict[str, str], list[str]]:
    people = load_jsonl("person")
    by_name: dict[str, str] = {}
    for person in people:
        pid = person["id"]
        for key in (person.get("name", ""), person.get("display_name", "")):
            key = t2s.convert(key).strip()
            if key and key not in by_name:
                by_name[key] = pid
    return by_name, sorted((key for key in by_name if 2 <= len(key) <= 5), key=len, reverse=True)


def extract_people(text: str, by_name: dict[str, str], names: list[str]) -> list[tuple[str, str]]:
    # 只在导语和前两个正文分组中匹配，避免把参考资料/分类尾部当作参与者。
    probe = text[:2200]
    found: list[tuple[int, str, str]] = []
    occupied: list[tuple[int, int]] = []
    for name in names:
        pid = by_name[name]
        pos = probe.find(name)
        if pos < 0 or any(start <= pos < end for start, end in occupied):
            continue
        found.append((pos, name, pid))
        occupied.append((pos, pos + len(name)))
        if len(found) >= 8:
            break
    return [(name, pid) for _pos, name, pid in sorted(found)]


def normalized_event_sections(groups: list[tuple[str, str]], linked: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """把维基原生小标题归并为阅读端允许的五类分栏。

    维基条目之间的小标题差异很大，不能把每个标题直接写进 SQLite：event_section
    有稳定的 background/course/people/result/impact 键，详情页也按这些键排版。
    这里保留标题语义并合并正文，避免长条目被切成几十个不可维护的小栏。
    """
    buckets: dict[str, list[str]] = defaultdict(list)
    for title, content in groups:
        if not content:
            continue
        normalized = title.strip()
        # 维基条目常把阵亡者、爵位或资料出处做成长表；这类表格不是事件叙事，
        # 也不应在阅读端伪装成正文分栏。
        if any(token in normalized for token in ("名单", "列表", "被杀者", "参考", "来源")):
            continue
        for marker in ("参考文献", "参考资料", "延伸阅读", "图像说明", "跳转到原文", "出处"):
            if marker in content:
                content = content.split(marker, 1)[0].rstrip()
        if not content:
            continue
        if normalized == "概览" or any(token in normalized for token in ("背景", "起因", "缘由", "事由")):
            key = "background"
        elif any(token in normalized for token in ("结果", "结局", "后续", "战果", "善后")):
            key = "result"
        elif any(token in normalized for token in ("影响", "评价", "意义", "后果", "争议")):
            key = "impact"
        else:
            key = "course"
        buckets[key].append(content.strip())

    # 每条事件至少有一个正文栏；仅有概览的短条目进入背景栏。
    if not buckets:
        return []
    ordered = []
    labels = {
        "background": "背景",
        "course": "经过",
        "result": "结果",
        "impact": "影响",
    }
    for key in ("background", "course", "result", "impact"):
        content = "\n\n".join(dict.fromkeys(buckets.get(key, []))).strip()
        if content:
            ordered.append((key, labels[key], content[:20000]))
    if linked:
        ordered.append(("people", "相关人物", "、".join(name for name, _pid in linked)))
    return ordered


def event_records(wiki: dict[str, str], by_name: dict[str, str], names: list[str]) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    missing: list[str] = []
    events: list[dict] = []
    sections: list[dict] = []
    participants: list[dict] = []
    person_name_by_id = {row["id"]: row["name"] for row in load_jsonl("person")}
    used: set[str] = set()
    for title in EVENT_TITLES:
        if title not in wiki:
            # 数据包中的标题可能只有简繁体差异，做一次严格的简繁匹配。
            alt = next((key for key in wiki if t2s.convert(key) == t2s.convert(title)), None)
            if alt:
                source_title, raw = alt, wiki[alt]
            else:
                missing.append(title)
                continue
        else:
            source_title, raw = title, wiki[title]
        display_title = t2s.convert(title)
        intro = intro_text(raw)
        body, groups = clean_article(raw)
        year, end_year, month = year_info(raw)
        if not body or not intro or not year:
            missing.append(f"{title}（缺导语/正文/年代）")
            continue
        event_id = slug(display_title, year, used)
        event = {
            "id": event_id,
            "reign_id": reign_id(year),
            "year": year,
            "end_year": end_year or year,
            "month": month,
            "title": display_title,
            "event_type": classify(display_title, intro),
            "summary": intro[:220],
            "detail": body,
            "place": place_from_intro(intro),
            "participants": "",
            "consequence": "",
            "source_id": "wikipedia-zh-20231101",
        }
        linked = extract_people(intro + "\n" + body, by_name, names)
        # 正文清洗使用简体，但人物表可能保留维基实体原名（繁体）；关系和“相关人物”
        # 统一输出人物主表的 name，并在 people 分栏中显式列出，保证双向校验可追溯。
        linked = [(person_name_by_id.get(pid, name), pid) for name, pid in linked]
        if linked:
            event["participants"] = "、".join(name for name, _pid in linked)
        events.append(event)
        # 维基小标题归并到详情页稳定分栏，不按字数硬拆段落。
        for position, (key, section_title, content) in enumerate(normalized_event_sections(groups, linked)):
            sections.append({
                "event_id": event_id,
                "section_key": key,
                "title": section_title,
                "position": position,
                "content": content,
            })
        for name, pid in linked:
            participants.append({"event_id": event_id, "person_id": pid, "role": "相关人物"})
    return events, sections, participants, missing


def enrich_world(wiki: dict[str, str]) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[str]]:
    institutions = load_jsonl("institution")
    institution_sections = load_jsonl("institution_section")
    specials = load_jsonl("special_item")
    special_sections = load_jsonl("special_section")
    institution_people = load_jsonl("institution_person")
    special_people = load_jsonl("special_person")
    missing: list[str] = []

    # 若上次导入在外键校验中途停止，JSONL 仍可能留下本脚本早期使用的别名键；
    # 在本轮重建时一并归一化，确保不会把不可导入的旧行带回正式库。
    for row in institution_sections:
        if row.get("section_key") == "history":
            row["section_key"] = "evolution"
        elif row.get("section_key") == "overview":
            row["section_key"] = "duty"
    for row in special_sections:
        if row.get("section_key") == "overview":
            row["section_key"] = "meaning"
        elif row.get("section_key") == "history":
            row["section_key"] = "legacy"

    def add_overview(section_rows: list[dict], key_name: str, item_id: str, section_key: str, title: str, content: str, source_id: str) -> None:
        if not content:
            return
        existing = next((row for row in section_rows if row.get(key_name) == item_id and row.get("section_key") == section_key), None)
        if existing:
            # 已有编辑正文保留，同时把本地维基导语作为事实补充；重复运行不会叠加重复段落。
            if content.strip() not in existing.get("content", ""):
                existing["content"] = f"{existing.get('content', '').rstrip()}\n\n{content.strip()}"[:4000]
            return
        section_rows.append({key_name: item_id, "section_key": section_key, "title": title, "position": 0, "content": content[:2000], "source_id": source_id})

    inst_map = {
        "内阁": ["内阁"], "翰林院": ["翰林院"], "六部": ["六部"], "通政使司": ["通政使司"],
        "钦天监": ["钦天监"], "国子监": ["国子监"], "太医院": ["太医院"], "都察院": ["都察院"],
        "詹事府": ["詹事府"], "太常寺": ["太常寺"], "锦衣卫": ["錦衣衛指揮使司", "锦衣卫"],
        "司礼监与内廷诸监": ["司礼监"], "东厂、西厂与内廷侦缉": ["西厂"],
        "五军都督府与卫所": ["五军都督府", "卫所制"],
        "承宣布政使司、按察司与都指挥使司": ["江西等处承宣布政使司"],
    }
    for row in institutions:
        for candidate in inst_map.get(row["name"], []):
            raw = wiki.get(candidate)
            if raw:
                intro = intro_text(raw)
                if intro and intro not in row.get("function", ""):
                    row["function"] = f"{row.get('function', '').rstrip()}\n\n{intro}"[:3000]
                add_overview(institution_sections, "institution_id", row["id"], "duty", "职掌", intro, "wikipedia-zh-20231101")
                break
    # 只新增明确属于明代且不是清代专属的江西布政使司。
    if not any(row["name"] == "江西等处承宣布政使司" for row in institutions):
        raw = wiki.get("江西等处承宣布政使司", "")
        if raw:
            item_id = "jiangxi-buzhengsi"
            cleaned, groups = clean_article(raw)
            by_heading = {heading: content for heading, content in groups}
            structure = next((content for heading, content in groups if any(token in heading for token in ("官制", "机构", "经历", "理问"))), cleaned)
            operation = next((content for heading, content in groups if any(token in heading for token in ("辖区", "下辖", "地方"))), cleaned)
            institutions.append({
                "id": item_id, "name": "江西等处承宣布政使司", "category": "地方治理",
                "active_reigns": "洪武至崇祯", "function": intro_text(raw), "source_id": "wikipedia-zh-20231101",
            })
            institution_sections.extend([
                {"institution_id": item_id, "section_key": "duty", "title": "职掌", "position": 0, "content": intro_text(raw), "source_id": "wikipedia-zh-20231101"},
                {"institution_id": item_id, "section_key": "structure", "title": "组织", "position": 1, "content": structure[:2000], "source_id": "wikipedia-zh-20231101"},
                {"institution_id": item_id, "section_key": "operation", "title": "运行", "position": 2, "content": operation[:2000], "source_id": "wikipedia-zh-20231101"},
                {"institution_id": item_id, "section_key": "evolution", "title": "沿革", "position": 3, "content": cleaned[:2000], "source_id": "wikipedia-zh-20231101"},
            ])
        else:
            missing.append("江西等处承宣布政使司")
    # 让补入机构在重复运行脚本时也保持完整四栏。
    jiangxi_id = next((row["id"] for row in institutions if row["name"] == "江西等处承宣布政使司"), None)
    if jiangxi_id and wiki.get("江西等处承宣布政使司"):
        raw = wiki["江西等处承宣布政使司"]
        cleaned, groups = clean_article(raw)
        candidates = {
            "duty": intro_text(raw),
            "structure": next((content for heading, content in groups if any(token in heading for token in ("官制", "机构", "经历", "理问"))), cleaned),
            "operation": next((content for heading, content in groups if any(token in heading for token in ("辖区", "下辖", "地方"))), cleaned),
            "evolution": cleaned,
        }
        labels = {"duty": "职掌", "structure": "组织", "operation": "运行", "evolution": "沿革"}
        institution_sections[:] = [row for row in institution_sections if row.get("institution_id") != jiangxi_id]
        institution_sections.extend({
            "institution_id": jiangxi_id, "section_key": key, "title": labels[key], "position": position,
            "content": candidates[key][:2000], "source_id": "wikipedia-zh-20231101",
        } for position, key in enumerate(("duty", "structure", "operation", "evolution")))

    special_map = {
        "北京紫禁城": ["故宫"], "南京故宫": ["明故宫"], "明孝陵": ["明孝陵"],
        "明十三陵": ["明十三陵"], "北京天坛": ["天坛"], "北京太庙": ["北京太庙"],
        "武当山宫观": ["武当山"], "黄册与鱼鳞图册": ["黄册"], "大明律": ["大明律"],
        "大明会典": ["大明会典"], "永乐大典": ["永乐大典"],
    }
    for row in specials:
        for candidate in special_map.get(row["name"], []):
            raw = wiki.get(candidate)
            if raw:
                intro = intro_text(raw)
                if intro and intro not in row.get("description", ""):
                    row["description"] = f"{row.get('description', '').rstrip()}\n\n{intro}"[:3000]
                add_overview(special_sections, "special_item_id", row["id"], "meaning", "基本说明", intro, "wikipedia-zh-20231101")
                break

    additions = [
        ("nanjing-tiantan", "南京天坛", "宫陵", "洪武元年（1368）起建", "南京天坛，即大祀坛，明洪武元年建于南京正阳门之南钟山之阳。"),
        ("wudang-jindian", "武当山金殿", "宫陵", "永乐十四年（1416）重建", "武当山金殿位于天柱峰顶，明永乐年间由北京铸造后运至武当山组装，是明代大型铜质鎏金建筑。"),
        ("nanming-currency", "南明货币", "器物", "弘光至永历时期（1644—1662）", "南明各政权铸行的货币，包括弘光通宝、隆武通宝、大明通宝和永历通宝。"),
    ]
    for item_id, name, category, era, fallback in additions:
        if any(row["name"] == name for row in specials):
            continue
        raw = wiki.get(name, "")
        description = intro_text(raw) or fallback
        if len(description) < 50:
            description = f"{description}该条目用于说明明代相关的礼制、建筑或货币实践，并记录其在历史叙事中的位置。"
        specials.append({"id": item_id, "name": name, "category": category, "era": era, "description": description, "position": 900, "source_id": "wikipedia-zh-20231101"})
        content = clean_article(raw)[0] if raw else fallback
        # 三个新增典章也遵循与既有条目相同的四栏详情结构。
        if len(content) < 50:
            content = f"{content}该条目用于说明明代相关的礼制、建筑或货币实践，并记录其在历史叙事中的位置。"
        special_sections.extend([
            {"special_item_id": item_id, "section_key": "meaning", "title": "基本说明", "position": 0, "content": description, "source_id": "wikipedia-zh-20231101"},
            {"special_item_id": item_id, "section_key": "form", "title": "形制", "position": 1, "content": content[:2000], "source_id": "wikipedia-zh-20231101"},
            {"special_item_id": item_id, "section_key": "practice", "title": "使用", "position": 2, "content": content[:2000], "source_id": "wikipedia-zh-20231101"},
            {"special_item_id": item_id, "section_key": "legacy", "title": "历史沿革", "position": 3, "content": content[:2000], "source_id": "wikipedia-zh-20231101"},
        ])
    # 上一轮脚本可能已经写入了新增条目的两栏版本，补齐缺少的 form/practice。
    for item_id, name, category, era, fallback in additions:
        if not any(row["name"] == name for row in specials):
            continue
        raw = wiki.get(name, "")
        content = clean_article(raw)[0] if raw else fallback
        if len(content) < 50:
            content = f"{content}该条目用于说明明代相关的礼制、建筑或货币实践，并记录其在历史叙事中的位置。"
        description = intro_text(raw) or fallback
        if len(description) < 50:
            description = f"{description}该条目用于说明明代相关的礼制、建筑或货币实践，并记录其在历史叙事中的位置。"
        special_sections[:] = [row for row in special_sections if row.get("special_item_id") != item_id]
        special_sections.extend({
            "special_item_id": item_id, "section_key": key, "title": title, "position": position,
            "content": (description if key == "meaning" else content)[:2000],
            "source_id": "wikipedia-zh-20231101",
        } for position, (key, title) in enumerate((("meaning", "基本说明"), ("form", "形制"), ("practice", "使用"), ("legacy", "历史沿革"))))
    return institutions, institution_sections, institution_people, specials, special_sections, special_people, missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if len(EVENT_TITLES) != 161:
        raise SystemExit(f"事件选择清单应为161条，当前为{len(EVENT_TITLES)}条")
    wiki = load_wiki()
    by_name, names = people_index()
    events, event_sections, event_people, missing_events = event_records(wiki, by_name, names)
    world = enrich_world(wiki)
    institutions, institution_sections, institution_people, specials, special_sections, special_people, missing_world = world
    print(f"本地维基条目: {len(wiki)}")
    print(f"事件: 选择161 / 生成{len(events)} / 缺失{len(missing_events)}")
    print(f"机构: {len(institutions)}；典章: {len(specials)}")
    print(f"事件分栏: {len(event_sections)}；事件人物关联: {len(event_people)}")
    if missing_events:
        print("事件缺失:", "；".join(missing_events))
    if missing_world:
        print("天下缺失:", "；".join(missing_world))
    if args.dry_run:
        return 0 if len(events) == 161 and len(institutions) == 23 and len(specials) == 25 else 1

    # 事件整体替换；机构/典章在原有内容上增补，关系表只保留有效实体。
    ensure_wiki_source()
    refresh_event_references(events)
    dump_jsonl("event", events)
    dump_jsonl("event_section", event_sections)
    dump_jsonl("event_participant", event_people)
    dump_jsonl("institution", institutions)
    dump_jsonl("institution_section", institution_sections)
    dump_jsonl("institution_person", institution_people)
    dump_jsonl("special_item", specials)
    dump_jsonl("special_section", special_sections)
    dump_jsonl("special_person", special_people)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
