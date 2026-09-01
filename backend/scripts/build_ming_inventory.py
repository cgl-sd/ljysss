#!/usr/bin/env python3
"""生成软件全部介绍内容的分类清单：每一项都给出名目、出处卷次与现有收录数。

清单按软件的实际栏目组织——岁月（事件）、人物（六分类·朝代档案·关系）、
天下（舆图·机构·典章）、以及各栏需要的说明字段。语料侧的名目从《明史》目录、
志部小节、本纪编年与表部世系机械抽取，库内侧从内容文本统计，两边一比就知道缺什么。

    backend/.venv/bin/python backend/scripts/build_ming_inventory.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
CORPUS = BACKEND / "sources" / "mingshi_full"
CONTENT = BACKEND / "data" / "content"
OUT_MARKDOWN = ROOT / "docs" / "ming-inventory.md"
OUT_JSON = ROOT / "docs" / "ming-inventory.json"

SUBSECTION = re.compile(r"^○([\u4e00-\u9fff·]{2,24})")
SECTION = re.compile(r"^◎([\u4e00-\u9fff·]{2,24})")
BIO_HEAD = re.compile(r"^([\u4e00-\u9fff·]{2,5})，(?:[^。\n]{0,14}字[^。\n]{1,10}|[^。\n]{0,26}?(?:人|籍[^。\n]{1,12})|太祖|成祖|子|妃|主)。")
DATE_ENTRY = re.compile(r"([元一二三四五六七八九十百]+年)(春|夏|秋|冬)?(正|二|三|四|五|六|七|八|九|十|十一|十二|腊)月")

# 志部十三志的卷界，与《明史》目录一致
TREATISES = [
    ("天文", 25, 27, "历象・天象记录"),
    ("五行", 28, 30, "灾异：地震、水旱、疾疫、虫霜"),
    ("历", 31, 39, "大统历、回回历"),
    ("地理", 40, 46, "两京十三省、属府州县、土司、卫所治所"),
    ("礼", 47, 60, "祭祀、朝仪、冠婚、丧葬、巡狩、封爵仪注"),
    ("乐", 61, 64, "乐章、祭乐、宴飨乐、卤簿乐"),
    ("舆服", 65, 68, "车辇卤簿、冕服冠服、宝玺册宝、仪仗器用"),
    ("选举", 69, 71, "学校、科目、荐举、铨选、封赠、荫叙"),
    ("职官", 72, 79, "中央与地方各衙门、员额、品秩"),
    ("食货", 80, 86, "户口、田制、屯田、赋役、漕运、盐法、茶法、钱币、采造"),
    ("兵", 87, 92, "卫所、都司、京营、军制、马政、边防海防"),
    ("刑法", 93, 95, "律例、廷杖、厂卫、诏狱、充军"),
    ("艺文", 96, 99, "经史子集四部书目"),
]

# 列传各段的收类，用于人物域与「四裔」域
BIOGRAPHY_BLOCKS = [
    ("后妃", 113, 115), ("宗室诸王", 116, 125), ("功臣・外戚", 126, 132),
    ("明臣列传", 133, 281), ("阉党・佞幸", 282, 284), ("文苑", 285, 294),
    ("儒林・循吏・孝义", 295, 304), ("隐逸・方技・奸臣", 305, 311),
    ("土司", 312, 319), ("外国・西域", 320, 332),
]


CONSORT_HEAD = re.compile(r"^([\u4e00-\u9fff·]{2,10}(?:皇后|太后|贵妃|皇妃|妃|公主|郡主))[，,]")
PRINCE_HEAD = re.compile(r"^([\u4e00-\u9fff·]{1,8}(?:亲王|郡王|王|公主|太子))[，,]")
BORDER_HEAD = re.compile(r"^([\u4e00-\u9fff·]{2,8})[，,]?\s*(?:，|东|西|南|北|去|距|与|在)")
EXTRA_HEADS = {
    "后妃": CONSORT_HEAD,
    "宗室诸王": PRINCE_HEAD,
    "土司": PRINCE_HEAD,
    "外国・西域": None,
}

def juan(number: int) -> Path:
    return CORPUS / f"卷{number:03d}.txt"


def lines_of(number: int) -> list[str]:
    path = juan(number)
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def volume_treatise(number: int) -> str:
    """志名取自卷首 ◎ 行，去掉末位次序数字：◎职官一 → 职官。"""

    for line in lines_of(number)[:4]:
        if (m := SECTION.match(line)):
            return re.sub(r"[一二三四五六七八九十]+$", "", m.group(1))
    return ""


def is_catalog_line(line: str) -> bool:
    parts = [p for p in re.split(r"\s{1,}", line) if p]
    return len(parts) >= 3 and all(len(p) <= 16 for p in parts)


def treatise_items_for(number: int) -> list[str]:
    """卷首区内的名目行与 ○ 小节标题即该志条目。

    《明史》常先排一段按语再排名目（职官志即如此），所以不能在遇到第一行正文时
    就中断，改为在卷首若干行内收集所有形如目录的行。
    """

    items: list[str] = []
    for line in lines_of(number)[1:17]:
        marker = SUBSECTION.match(line)
        if marker:
            pieces = re.split(r"\s{1,}", marker.group(1))
        elif is_catalog_line(line):
            pieces = re.split(r"\s{1,}", line)
        else:
            continue
        items += [p for p in pieces if 2 <= len(p) <= 16 and not p.startswith(("附", "（", "("))]
    volume_like = re.compile(r"[\u4e00-\u9fff]{1,4}[一二三四五六七八九十]{1,3}")
    return [item for item in items if not volume_like.fullmatch(item)]


def all_treatise_items() -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for number in range(25, 100):
        name = volume_treatise(number)
        if not name:
            continue
        buckets.setdefault(name, [])
        buckets[name] += treatise_items_for(number)
    return {name: list(dict.fromkeys(items)) for name, items in buckets.items()}


def biography_heads(start: int, stop: int, extra: re.Pattern | None = None) -> list[str]:
    heads: list[str] = []
    for j in range(start, stop + 1):
        for line in lines_of(j)[1:]:
            if (m := BIO_HEAD.match(line)) or (extra and (m := extra.match(line))):
                heads.append(m.group(1))
    return list(dict.fromkeys(heads))


def annals_entries(start: int, stop: int) -> int:
    return sum(len(DATE_ENTRY.findall("\n".join(lines_of(j)))) for j in range(start, stop + 1))


def read_jsonl(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def store_counts() -> dict:
    people = read_jsonl("person")
    relics = read_jsonl("special_item")
    events = read_jsonl("event")
    return {
        "人物总数": len(people),
        "人物按类": dict(Counter(p["category"] for p in people)),
        "典章总数": len(relics),
        "典章按组": dict(Counter(r["category"] for r in relics)),
        "典章缺年代": sum(1 for r in relics if not r.get("era", "").strip()),
        "事件总数": len(events),
        "事件按年号": dict(Counter(e["reign_id"] for e in events)),
        "关系边": len(read_jsonl("person_relation")),
        "机构数": len(read_jsonl("institution")),
    }


def main() -> None:
    treatise = all_treatise_items()
    biographies = {
        name: biography_heads(start, stop, EXTRA_HEADS.get(name))
        for name, start, stop in BIOGRAPHY_BLOCKS
    }
    annals = {
        "本纪逐月记事": annals_entries(1, 24),
        "诸王世表条目": len([line for j in range(100, 113) for line in lines_of(j)
                             if re.match(r"^[\u4e00-\u9fff]{1,6}[王公主]", line)]),
    }
    store = store_counts()
    reigns = sorted(read_jsonl("reign"), key=lambda row: row["start_year"])
    order = [name for name, _, _, _ in TREATISES if name in treatise] + \
            [name for name in treatise if name not in {n for n, _, _, _ in TREATISES}]
    treatise = {name: treatise[name] for name in order}

    def items_of(*names: str) -> list[str]:
        for label in names:
            if treatise.get(label):
                return treatise[label]
        return []

    def named(name_list: list[str], fallback: str) -> str:
        return "、".join(name_list) if name_list else fallback

    doc: list[str] = [
        "# 软件内容总清单",
        "",
        "由 `backend/scripts/build_ming_inventory.py` 生成，语料为《明史》332 卷定形本。",
        "「应收」是《明史》目录里确有此项的数量，「现有」是当前内容库的条数。",
        "",
        "## 一、人物（人物页・六分类）",
        "",
        "| 列传区块 | 卷次 | 应收（传主） |",
        "|---|---|---|",
    ]
    for name, start, stop in BIOGRAPHY_BLOCKS:
        doc.append(f"| {name} | 卷{start}–{stop} | {len(biographies[name])} |")
    total_heads = sum(len(v) for v in biographies.values())
    doc += [
        f"| **合计** | 卷113–332 | **{total_heads}** |",
        "",
        f"现有 {store['人物总数']} 人，分布：" + "、".join(f"{k} {v}" for k, v in store["人物按类"].items()),
        "",
        "每条需要的介绍：姓名 / 字与号 / 生卒 / 封号谥号（帝王与藩王）/ 籍贯 /",
        "分类（六类之一）/ 年号 / 生平四段（早年・入仕・事迹・终局）/ 家族成员与结局 /",
        "人物关系边 / 相关事件 / 每段出处（《明史》卷次＋维基条目＋CBDB 人物码）。",
        "",
        "## 二、事件（岁月页）",
        "",
        f"- 《明史》本纪逐月编年：**{annals['本纪逐月记事']} 条**（卷1–24，每条自带帝、年、月，可直接作出处）",
        f"- 现有 {store['事件总数']} 件精选大事；正文小标题归并为背景、经过、相关人物、结果、影响等稳定分栏，至少保留一个正文栏",
        "",
        "| 时段 | 年份 | 本纪编年条数 | 现有事件 |",
        "|---|---|---|---|",
    ]
    for reign in reigns:
        years = str(reign["start_year"]) if reign["start_year"] == reign["end_year"] else \
            f"{reign['start_year']}—{reign['end_year']}"
        doc.append(
            f"| {reign['title']} | {years} | — | {store['事件按年号'].get(reign['id'], 0)} |"
        )
    doc += [
        "",
        "每条需要的介绍：标题 / 年 / 月（有则必填）/ 地点 / 背景 / 经过 /",
        "相关人物（存 person.id，可点进详情）/ 结果 / 影响 / 出处（《明史》本纪某卷）。",
        "",
        "## 三、机构（天下页・机构）",
        "",
        f"- 志・职官 小节 **{len(treatise.get('职官', []))} 项**",
        f"- 现有 {store['机构数']} 个",
        "",
        named(treatise.get("职官", []), "（未取到职官名目）"),
        "",
        "每个机构需要的介绍：职掌 / 员额与品秩 / 选任与考课 / 沿革（洪武至崇祯）/",
        "下属机构与卫所 / 升转路径 / 典型任职者（链到人物）/ 出处（《明史》职官志某卷）。",
        "",
        "## 四、典章：制度、器物、礼乐、习俗（天下页・典章）",
        "",
        "| 志 | 卷次 | 应收条目 | 现有 | 软件分组 |",
        "|---|---|---|---|---|",
    ]
    grouped = {"职官": "制度", "舆服": "器物", "礼": "习俗", "乐": "专题", "选举": "制度",
               "食货": "制度", "兵": "制度", "刑法": "制度", "刑": "制度", "地理": "宫阙",
               "历": "专题", "历法": "专题", "天文": "专题", "五行": "专题", "艺文": "专题"}
    for name, items in treatise.items():
        volumes = [j for j in range(25, 100) if volume_treatise(j) == name]
        span = f"卷{min(volumes)}–{max(volumes)}" if volumes else "—"
        count = len(items) or "名目在志文内，需另抽"
        doc.append(f"| {name} | {span} | {count} | — | {grouped.get(name, '专题')} |")
    doc += [
        f"| **合计** | 卷25–99 | **{sum(len(v) for v in treatise.values())}** | "
        f"{store['典章总数']}（其中缺年代 {store['典章缺年代']}） | |",
        "",
        "### 舆服与器物名目（含官服制度）",
        "",
        named(items_of("舆服"), "（未取到，需按传文另抽）"),
        "",
        "### 礼制与习俗名目",
        "",
        named(items_of("礼", "礼仪"), "（未取到）"),
        "",
        "### 食货・兵・刑名目",
        "",
        "食货：" + named(items_of("食货"), "（未取到）"),
        "",
        "兵：" + named(items_of("兵"), "（未取到）"),
        "",
        "刑法：" + named(items_of("刑", "刑法"), "（志部无 ○ 标记，需按传文另抽）"),
        "",
        "每条典章需要的介绍：定名 / 年代与定制年份 / 形制或职掌 / 等级与使用资格 /",
        "运作方式 / 一条具体史实例 / 出处（《明史》某志某卷）。",
        "",
        "## 五、宗室与世系（宗藩栏与家族栏的骨架）",
        "",
        f"- 表・诸王与功臣世系可提取条目 **{annals['诸王世表条目']} 条**（卷100–112）",
        "  每条形如「楚昭王桢，太祖庶六子，洪武三年封。十四年就藩…庄王孟烷，昭嫡三子…」，",
        "  即封号↔本名世次↔封年，是把「代简王桂」这类称谓对回「朱桂」的映射源。",
        f"- 列传・宗室诸王（卷116–125）传主 {len(biographies['宗室诸王'])} 人",
        "",
        "## 六、地理与舆图",
        "",
        f"- 志・地理（卷40–46）小节 {len(treatise['地理'])} 项：两京十三省、属府州县、土司、卫所治所",
        "- 缺：现代地图底图与历史政区矢量数据（边界坐标无法从《明史》得到，需另找数据源）",
        "",
        "## 七、四裔与交往（当前完全未开域）",
        "",
        f"- 列传・土司（卷312–319）{len(biographies['土司'])} 项；外国与西域（卷320–332）{len(biographies['外国・西域'])} 项",
        "- 旧收录脚本按「卷≥300 为政权非人物」整段排除，导致对外关系这一整块为空",
        "",
        "## 八、软件栏目需要的说明字段汇总",
        "",
        "| 栏目 | 必需字段 | 可省略条件 |",
        "|---|---|---|",
        "| 岁月・事件卡 | 年月日、地点、背景、经过、相关人物、结果、影响、出处 | 无实料整栏隐藏 |",
        "| 人物・详情 | 姓名、字号、生卒、官职或封号谥号、年号、生平四段、家族、人物关系、相关事件、出处行 | 无实料整栏隐藏 |",
        "| 人物・朝代档案 | 年号起讫、本朝摘要、六分类分组名录 | — |",
        "| 人物・关系 | 本人一端的边、类型、共同事件、备注、出处 | 无边的人物不显示 |",
        "| 天下・舆图 | 政区名、两京、省治、周边政权、时间轴、事件点 | — |",
        "| 天下・机构 | 职掌、员额品秩、沿革、升转、典型任职者、出处 | — |",
        "| 天下・典章 | 定名、年代、形制职掌、等级资格、史实例、出处 | 消歧义页与 <60 字残条一律不收 |",
    ]
    OUT_MARKDOWN.write_text("\n".join(doc) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"志部": {k: v for k, v in treatise.items()},
         "列传": {k: v for k, v in biographies.items()},
         "本纪": annals, "库内": store}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"清单已生成：{OUT_MARKDOWN.relative_to(ROOT)} 与 {OUT_JSON.relative_to(ROOT)}")
    print(f"\n应收合计：人物 {total_heads}｜典章制度器物 {sum(len(v) for v in treatise.values())}"
          f"｜本纪编年 {annals['本纪逐月记事']}｜世系 {annals['诸王世表条目']}")
    print(f"库内现有：人物 {store['人物总数']}｜典章 {store['典章总数']}｜事件 {store['事件总数']}"
          f"｜机构 {store['机构数']}｜关系 {store['关系边']}")


if __name__ == "__main__":
    main()
