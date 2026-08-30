#!/usr/bin/env python3
"""将已初核的人物资料整理为可直接发布的正式内容库。

本脚本只改 ``data/content`` 中的最终人物字段与生平栏目，不写审核时间、状态或
报告表。证据来自本地中文维基全文、既有来源登记和《明史》锚点；无法得到可展示
正式称号的条目会被列为阻断错误，绝不以“明朝官员”等泛称入库。

    .venv/bin/python scripts/finalize_people_catalog.py --check
    .venv/bin/python scripts/finalize_people_catalog.py --apply
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"
NORMALIZE_PATH = BACKEND / "scripts" / "normalize_person_profiles.py"
SPEC = importlib.util.spec_from_file_location("normalize_person_profiles", NORMALIZE_PATH)
assert SPEC and SPEC.loader
NORMALIZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NORMALIZE)

GENERIC = re.compile(r"^(?:明(?:朝|代)?(?:官员|官員|将领|將領|人物|藩王|文人|勋臣|勳臣)|"
                     r"政治人物|军事人物|軍事人物|军事将领|軍事將領|官员|官員|将领|將領|武烈|文(?:忠|武|贞|貞|靖|端|定)|)$")
BAD = re.compile(r"(?:\?|[A-Za-z]|明(?:朝|代)?(?:官员|官員|将领|將領|人物|藩王|文人|勋臣|勳臣))")
BAD_TITLE_PREFIX = re.compile(
    r"^(?:字|号|號|名|又称|又稱|其|他|她|与|與|因|被|请|請|随|隨|从|從|由|获|獲|受|于是|於是|"
    r"当时|當時|时|時|曾|后来|後來|此后|此後|跟从|跟隨|朱元璋|皇帝|王|妃)"
)
ROLE_ENDINGS = (
    "内阁首辅", "內閣首輔", "大学士", "大學士", "尚书", "尚書", "侍郎", "都御史", "总督", "總督", "巡抚", "巡撫",
    "督师", "督師", "都督", "指挥使", "指揮使", "总兵官", "總兵官", "总兵", "總兵", "副总兵", "副總兵", "参将", "參將",
    "游击", "游擊", "将军", "將軍", "布政使", "按察使", "知府", "知县", "知縣", "御史", "给事中", "給事中", "祭酒",
    "学士", "學士", "编修", "編修", "检讨", "檢討", "主事", "郎中", "通政使", "寺卿", "太保", "太傅", "太师", "太師", "推官",
    "孔目", "学正", "學正", "行人", "博士", "评事", "評事", "知事", "千户", "千戶", "副千户", "副千戶", "卫副千户", "衛副千戶",
    "进士", "進士", "举人", "舉人", "教谕", "教諭", "训导", "訓導", "县丞", "縣丞", "县尉", "縣尉", "经历", "經歷",
    "少卿", "典籍", "长史", "長史", "御医", "御醫", "典史", "教授", "员外郎", "員外郎", "应奉", "應奉", "山长", "山長",
    "通判", "知州", "太学生", "太學生", "丞相", "丞相", "参政", "參政", "参议", "參議", "学政", "學政",
    "少保", "少傅", "少师", "少師", "皇后", "太后", "太皇太后", "皇贵妃", "皇貴妃", "贵妃", "貴妃", "妃", "嫔", "嬪",
    "选侍", "選侍", "太监", "太監", "内官", "內官", "女官", "乳母", "世子", "驸马", "駙馬", "诗人", "詩人", "文学家",
    "文學家", "书法家", "書法家", "画家", "畫家", "医家", "醫家", "戏曲家", "戲曲家", "思想家", "藏书家", "藏書家",
)
ROLE = re.compile(r"[一-龥]{0,14}(?:" + "|".join(sorted(map(re.escape, ROLE_ENDINGS), key=len, reverse=True)) + r")")
NOBLE = re.compile(r"[一-龥]{1,8}(?:亲王|親王|郡王|王|国公|國公|公|侯|伯|公主)")
# “太子太傅”等官衔不是储君；只接受皇太子或以太子结尾的正式名号。
CROWN = re.compile(r"(?:皇太子|太子)$")
DISPLAY_NAME = re.compile(r"(?:本名|讳|諱|名(?:为|為|曰))\s*[：:]?\s*(朱[一-龥]{1,4})")
IDENTITY = re.compile(r"(?:孝子|民变领袖|民變領袖|军事将领|軍事將領|针灸学家|針灸學家|山林逸士|策士|外戚)")
IMPERIAL = re.compile(r"明(?:太祖|成祖|仁宗|宣宗|英宗|代宗|宪宗|憲宗|孝宗|武宗|世宗|穆宗|神宗|光宗|熹宗|思宗|安宗|绍宗|紹宗|昭宗)")
# 在位君主的称号以编目主档为准，不能从正文中误取父祖或后继者的庙号。
EMPEROR_TITLES = {
    "zhuyuanzhang": "明太祖", "zhuyunwen": "明惠帝", "zhudi": "明成祖", "zhugaochi": "明仁宗",
    "zhuzhanji": "明宣宗", "zhuqizhen": "明英宗", "zhuqiyu": "明代宗", "zhujian": "明宪宗",
    "zhuyoutang": "明孝宗", "zhuhouzhao": "明武宗", "zhuhoucong": "明世宗", "zhuzaihou": "明穆宗",
    "zhuyijun": "明神宗", "zhuchangluo": "明光宗", "zhuyouxiao": "明熹宗", "zhuyoujian": "明思宗",
    "zhuyousong": "弘光帝", "zhuyujian": "隆武帝", "zhuyoulang": "永历帝", "zhuchangfang": "潞王监国",
    "zhuyihai": "鲁王监国", "zhuyuyu": "绍武帝",
}
# 这些条目的身份在导语中有明确文字，只是没有标准信息框可供通用职衔式抽取。
SOURCE_TITLE_OVERRIDES = {
    "chenji": "右春坊左赞",
    "chenzhong": "都指挥同知",
    "huobin": "武举人",
    "lidan": "甲必丹",
    "liushihuan": "广东按察司佥事",
    "niujingxian": "监察御史",
    "qingwensheng": "龙阳典史",
    "wangjin-2": "宁波知府",
    "xieyingfang": "常州府学教授",
    "yanben": "刑部主事",
    "zhaojie": "布衣",
    "zhangbing": "工部右侍郎",
    "zhoujingxin": "太学生",
}
# 原始名录中混入的非人物/非明条目，或虽为明人却没有可核验正式第二行名号的条目。
# 发布库不以“明朝人物”“义士”等泛称补位，直接移出。
EXCLUDED_IDS = {"luanfeng", "wangmiaofeng", "wude", "zhangying", "zhengzunqian"}


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(name: str, rows: list[dict]) -> None:
    (CONTENT / f"{name}.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )


def clean_title(value: str) -> str:
    value = NORMALIZE.simplify_modern_text(value or "")
    value = re.sub(r"（[^）]*）|\([^)]*\)", "", value or "")
    value = value.split("→")[0].split("，")[0].split("；")[0].strip(" 、，；：。")
    value = re.sub(r"^(?:明(?:朝|代)|中国明朝|中國明朝)", "", value)
    # 职衔只取动作词后的名词部分，避免把“朱元璋任命其为大都督”整句当作称号。
    value = re.sub(
        r"^.{0,20}(?:任命其为|任命其為|曾任|历任|歷任|官至|仕至|累官至|官拜|拜为|拜為|"
        r"授予|授为|授為|出任|担任|擔任|升任|迁任|遷任|升为|升為|进为|進為|封为|封為|追封为|追封為)",
        "", value,
    )
    # 同一短语可能有“授任”“升任”等两个动作词，循环消掉后只留下职衔。
    for _ in range(3):
        updated = re.sub(
            r"^(?:(?:[一二三四五六七八九十〇零\d]+年|[一二三四五六七八九十〇零\d]+月|本年|次月|翌年|后来|後來|此后|此後)"
            r"(?:[一二三四五六七八九十〇零\d]+月)?|由[一-龥]{1,8}(?:擢|举|舉|荐|薦))?"
            r"(?:官至|官终|官終|官|仕至|累官至|历任|歷任|授|任|迁|遷|升|晋升|晉升|拜为|拜為|为|為|是|进|進|改|擢|转|轉|后|後|起用|起)",
            "", value,
        )
        if updated == value:
            break
        value = updated
    return value.strip()


def valid_title(value: str) -> bool:
    return bool(
        value and len(value) <= 18 and not GENERIC.fullmatch(value) and not BAD.search(value)
        and not BAD_TITLE_PREFIX.search(value) and not re.search(r"[任升改擢]|(?:为|為|由|以)", value)
        and ("授" not in value or value.endswith("教授"))
    )


def candidates(text: str) -> list[str]:
    text = text.replace("\n", " ")[:1600]
    result: list[str] = []
    for pattern in (ROLE, NOBLE, IDENTITY):
        for match in pattern.finditer(text):
            value = clean_title(match.group())
            if valid_title(value):
                result.append(value)
    return result


def title_score(value: str, category: str) -> tuple[int, int]:
    high_office = ("首辅", "首輔", "大学士", "大學士", "尚书", "尚書", "总督", "總督", "巡抚", "巡撫", "都御史", "督师", "督師")
    military = ("总兵", "總兵", "都督", "指挥", "指揮", "将军", "將軍", "参将", "參將", "游击", "游擊")
    court = ("皇后", "太后", "妃", "嫔", "选侍", "太监", "內官", "内官")
    noble = ("亲王", "親王", "郡王", "王", "公", "侯", "伯", "公主")
    if category == "内廷" and value.endswith(court):
        return (0, len(value))
    if category == "宗藩" and value.endswith(noble):
        return (0, len(value))
    if category == "将帅" and any(key in value for key in military):
        return (0, len(value))
    if any(key in value for key in high_office):
        return (0, len(value))
    if value.endswith(("员外郎", "員外郎", "少卿", "知州", "知府", "知县", "知縣", "通判", "长史", "長史", "推官", "御史")):
        return (1, len(value))
    return (2, len(value))


def choose_source_title(person: dict, wiki: str) -> str:
    category = person.get("category", "")
    wiki = NORMALIZE.simplify_modern_text(wiki)
    lead = "\n".join(wiki.split("\n\n")[:2])
    # 封爵/追封的受封者与爵号同句，是最稳定的非信息框称号来源。
    granted = re.findall(
        r"(?:追封|进封|進封|加封|受封|封为|封為|封|赠|贈)\s*(?:其|他)?(?:为|為)?\s*"
        r"([一-龥]{1,8}(?:亲王|親王|郡王|王|国公|國公|公|侯|伯))",
        wiki[:3000],
    )
    granted = [clean_title(item) for item in granted]
    granted = [item for item in granted if len(item) >= 2 and valid_title(item)]
    if granted:
        return granted[0]
    if "外戚" in lead:
        return "外戚"
    direct = candidates(lead)
    # 没有“封/受封”语境时，正文出现的某王、某侯大多是其他人物，不能借用。
    direct = [item for item in direct if not item.endswith(("王", "公", "侯", "伯"))]
    if direct:
        return min(direct, key=lambda item: title_score(item, category))
    # 词条导语没有职位时，才从开头的叙事和条目分类取一个明确的传主身份。
    fallback = [item for item in candidates(wiki[:1600]) if not item.endswith(("王", "公", "侯", "伯"))]
    return min(fallback, key=lambda item: title_score(item, category)) if fallback else ""


def canonical_title(person: dict, wiki: str, baseline_title: str | None = None) -> str:
    name = person["name"].strip()
    if person["id"] in EMPEROR_TITLES:
        return EMPEROR_TITLES[person["id"]]
    raw_old = person.get("title", "") if baseline_title is None else baseline_title
    old = clean_title(raw_old)
    # 旧档中的“吴王世子、皇太子”等为本人名号，而非正文出现的他人称号。
    # 只接受末项为太子的名号，避免把“太子太傅”等官衔误迁。
    direct_crown = re.search(r"(?:皇太子|[一-龥]{1,6}太子)(?!太保|太傅|少保|少傅)", raw_old or "")
    if name.startswith("朱") and direct_crown:
        return "皇太子"
    if name.endswith("公主"):
        return name
    if name.endswith("皇后"):
        return "皇后"
    if name == "叶兑":  # 《明史·卷一三五》明确记作“以布衣献书太祖”。
        return "布衣"
    if person["id"] in SOURCE_TITLE_OVERRIDES:
        return SOURCE_TITLE_OVERRIDES[person["id"]]
    if valid_title(old) and "太子" not in old:
        exact = candidates(old)
        return min(exact, key=lambda item: title_score(item, person.get("category", ""))) if exact else old
    source_title = choose_source_title(person, wiki)
    if source_title:
        return source_title
    return ""


def display_name(person: dict, wiki: str) -> str:
    if person.get("category") == "宗藩" and person["name"].endswith("公主"):
        match = DISPLAY_NAME.search(f"{person.get('summary', '')}\n{wiki[:1200]}")
        if match:
            return match.group(1)
    return person["name"]


def corrected_category(person: dict, wiki: str, title: str, baseline_category: str) -> str:
    """只以传主导语和其本人正式称号定类，亲属称号不能把人拖入内廷。"""

    if person["id"] in EMPEROR_TITLES or title == "皇太子":
        return "帝王"
    # 原名录的六分类是人物自身身份的基线；本轮只按可证明的储君和高阶官职作迁移。
    # 不再扫描全文，以免亲属的后妃、王爵、军职改变传主分类。
    if re.search(r"(?:首辅|首輔|大学士|大學士|尚书|尚書|侍郎|都御史|总督|總督|巡抚|巡撫|御史|知府|知县|知縣|学士|學士|编修|編修|主事|员外郎|員外郎|通判|知州)", title):
        return "朝臣"
    if baseline_category in {"帝王", "内廷", "宗藩", "朝臣", "将帅", "文苑"}:
        return baseline_category
    return person["category"]


def clean_life_residue(content: str) -> str:
    """删除维基分类尾部残留的拉丁字符与抓取乱码，保留中文叙事句读。"""

    content = re.sub(r"[A-Za-z][A-Za-z0-9 .:_/\-]*", "", content)
    content = content.replace("?", "")
    content = re.sub(r"[（(]\s*[）)]", "", content)
    content = re.sub(r"[ \t]+", "", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def has_ming_anchor(references: list[dict], person_id: str, mingshi_ids: set[str]) -> bool:
    return person_id in mingshi_ids or any(
        row.get("content_type") == "person" and row.get("content_id") == person_id
        and ("明史" in row.get("locator", "") or "zh.wikipedia.org" in row.get("url", ""))
        for row in references
    )


def finalize(apply: bool, baseline: Path | None = None) -> tuple[int, list[str]]:
    names = [
        "person_category", "person_section_definition", "person", "person_wiki", "person_mingshi",
        "person_section", "content_reference", "person_research", "person_relation", "person_kin",
        "event_participant", "annal_participant", "person_cbdb",
    ]
    tables = {name: load(name) for name in names}
    baseline_titles = {}
    baseline_categories = {}
    if baseline:
        baseline_rows = [json.loads(line) for line in baseline.read_text(encoding="utf-8").splitlines() if line.strip()]
        baseline_titles = {row["id"]: row.get("title", "") for row in baseline_rows}
        baseline_categories = {row["id"]: row.get("category", "") for row in baseline_rows}
    # Existing normalization already holds the vetted, source-driven rules for life and category.
    NORMALIZE.normalize_tables(tables)
    for row in tables["person_section"]:
        if row["section_key"] == "life":
            row["content"] = clean_life_residue(row["content"])
    wiki = {row["person_id"]: row.get("full_text", "") for row in tables["person_wiki"]}
    mingshi_ids = {row["person_id"] for row in tables["person_mingshi"]}
    unresolved: list[str] = []
    for person in tables["person"]:
        full_text = wiki.get(person["id"], "")
        person["title"] = canonical_title(person, full_text, baseline_titles.get(person["id"]))
        person["display_name"] = display_name(person, full_text)
        person["category"] = corrected_category(
            person, full_text, person["title"], baseline_categories.get(person["id"], person["category"])
        )
        if not valid_title(person["title"]):
            unresolved.append(f"{person['id']}（{person['name']}：无正式称号）")
        if not person["display_name"].strip():
            unresolved.append(f"{person['id']}（无显示姓名）")
        if not has_ming_anchor(tables["content_reference"], person["id"], mingshi_ids):
            unresolved.append(f"{person['id']}（缺少明代或维基锚点）")

    for person in tables["person"]:
        body = next((row["content"] for row in tables["person_section"]
                     if row["person_id"] == person["id"] and row["section_key"] == "life"), "")
        if body:
            person["biography"] = body
            person["summary"] = re.sub(r"\s+", " ", body)[:120]

    # 逐条生平不允许把抓取残留带入正式库。
    life_by_id = {row["person_id"]: row["content"] for row in tables["person_section"] if row["section_key"] == "life"}
    for person in tables["person"]:
        body = life_by_id.get(person["id"], "")
        if not body.strip():
            unresolved.append(f"{person['id']}（缺少生平）")
        if re.search(r"[A-Za-z]|[?]|[（(]\s*[）)]", body):
            unresolved.append(f"{person['id']}（生平有英文、问号或空括号）")

    published_ids = {person["id"] for person in tables["person"] if person["id"] not in EXCLUDED_IDS}
    # 以人物表为唯一发布名录，级联剔除已移出人物的正文、关系、家族和参与记录，
    # 使 JSONL 重建 SQLite 后不存在孤儿行。
    if EXCLUDED_IDS:
        tables["person"] = [row for row in tables["person"] if row["id"] in published_ids]
        for name in ("person_wiki", "person_mingshi", "person_section", "person_research", "person_cbdb"):
            tables[name] = [row for row in tables[name] if row["person_id"] in published_ids]
        tables["content_reference"] = [
            row for row in tables["content_reference"]
            if row.get("content_type") != "person" or row.get("content_id") in published_ids
        ]
        tables["person_relation"] = [
            row for row in tables["person_relation"]
            if row["from_person_id"] in published_ids and row["to_person_id"] in published_ids
        ]
        tables["person_kin"] = [
            row for row in tables["person_kin"]
            if row["person_id"] in published_ids and (not row.get("kin_person_id") or row["kin_person_id"] in published_ids)
        ]
        for name in ("event_participant", "annal_participant"):
            tables[name] = [row for row in tables[name] if row["person_id"] in published_ids]
        unresolved = [message for message in unresolved if message.split("（", 1)[0] not in EXCLUDED_IDS]

    if unresolved:
        return len(tables["person"]), sorted(set(unresolved))
    if apply:
        for name in (
            "person", "person_wiki", "person_mingshi", "person_section", "content_reference", "person_research",
            "person_relation", "person_kin", "event_participant", "annal_participant", "person_cbdb",
        ):
            dump(name, tables[name])
    return len(tables["person"]), []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--baseline", type=Path, help="导入前的既有称号快照，仅用于一次性重建")
    args = parser.parse_args()
    count, unresolved = finalize(args.apply, args.baseline)
    if unresolved:
        raise SystemExit("人物正式库未完成：\n" + "\n".join(unresolved[:80]) + ("\n……" if len(unresolved) > 80 else ""))
    print(f"人物正式库已通过：{count} 人")


if __name__ == "__main__":
    main()
