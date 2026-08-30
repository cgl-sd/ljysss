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
                     r"政治人物|军事人物|軍事人物|官员|官員|将领|將領|武烈|文(?:忠|武|贞|貞|靖|端|定)|)$")
BAD = re.compile(r"(?:\?|[A-Za-z]|明(?:朝|代)?(?:官员|官員|将领|將領|人物|藩王|文人|勋臣|勳臣))")
ROLE_ENDINGS = (
    "内阁首辅", "內閣首輔", "大学士", "大學士", "尚书", "尚書", "侍郎", "都御史", "总督", "總督", "巡抚", "巡撫",
    "督师", "督師", "都督", "指挥使", "指揮使", "总兵官", "總兵官", "总兵", "總兵", "副总兵", "副總兵", "参将", "參將",
    "游击", "游擊", "将军", "將軍", "布政使", "按察使", "知府", "知县", "知縣", "御史", "给事中", "給事中", "祭酒",
    "学士", "學士", "编修", "編修", "检讨", "檢討", "主事", "郎中", "通政使", "寺卿", "太保", "太傅", "太师", "太師", "推官",
    "孔目", "学正", "學正", "行人", "博士", "评事", "評事", "知事", "千户", "千戶", "副千户", "副千戶", "卫副千户", "衛副千戶",
    "进士", "進士", "举人", "舉人", "教谕", "教諭", "训导", "訓導", "县丞", "縣丞", "县尉", "縣尉", "经历", "經歷",
    "少卿", "典籍", "长史", "長史", "御医", "御醫", "典史", "教授", "员外郎", "員外郎", "应奉", "應奉", "山长", "山長",
    "通判", "知州", "太学生", "太學生",
    "少保", "少傅", "少师", "少師", "皇后", "太后", "太皇太后", "皇贵妃", "皇貴妃", "贵妃", "貴妃", "妃", "嫔", "嬪",
    "选侍", "選侍", "太监", "太監", "内官", "內官", "女官", "乳母", "世子", "驸马", "駙馬", "诗人", "詩人", "文学家",
    "文學家", "书法家", "書法家", "画家", "畫家", "医家", "醫家", "戏曲家", "戲曲家", "思想家", "藏书家", "藏書家",
)
ROLE = re.compile(r"[一-龥]{0,14}(?:" + "|".join(sorted(map(re.escape, ROLE_ENDINGS), key=len, reverse=True)) + r")")
NOBLE = re.compile(r"[一-龥]{1,8}(?:亲王|親王|郡王|王|国公|國公|公|侯|伯|公主)")
# “太子太傅”等官衔不是储君；只接受皇太子或以太子结尾的正式名号。
CROWN = re.compile(r"(?:皇太子|太子)$")
DISPLAY_NAME = re.compile(r"(?:本名|讳|諱|名(?:为|為|曰))\s*[：:]?\s*(朱[一-龥]{1,4})")
IDENTITY = re.compile(r"(?:孝子|民变领袖|民變領袖|军事将领|軍事將領|针灸学家|針灸學家|山林逸士|策士)")
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
    value = re.sub(r"^(?:官至|仕至|累官至|历任|歷任|授|任|迁|遷|升|晋升|晉升|拜为|拜為|为|為)", "", value)
    return value.strip()


def valid_title(value: str) -> bool:
    return bool(value and len(value) <= 18 and not GENERIC.fullmatch(value) and not BAD.search(value))


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
    lead = wiki.split("\n\n", 1)[0]
    emperor = IMPERIAL.search(lead)
    if emperor:
        return emperor.group()
    direct = candidates(lead)
    if direct:
        return min(direct, key=lambda item: title_score(item, category))
    # 词条导语没有职位时，才从开头的叙事和条目分类取一个明确的传主身份。
    fallback = candidates(wiki[:1600])
    return min(fallback, key=lambda item: title_score(item, category)) if fallback else ""


def canonical_title(person: dict, wiki: str) -> str:
    name = person["name"].strip()
    if person["id"] in EMPEROR_TITLES:
        return EMPEROR_TITLES[person["id"]]
    old = clean_title(person.get("title", ""))
    source = f"{person.get('summary', '')}\n{wiki}"
    lead = wiki[:360]
    direct_crown = re.search(r"(?:册封|冊封|封为|封為|立为|立為).{0,8}皇太子|(?:哀冲|哀沖|庄敬|莊敬|懿文|献愍|獻愍)太子", lead)
    if name.startswith("朱") and direct_crown:
        return "皇太子"
    if name.endswith("公主"):
        return name
    if name.endswith("皇后"):
        return "皇后"
    if name == "叶兑":  # 《明史·卷一三五》明确记作“以布衣献书太祖”。
        return "布衣"
    source_title = choose_source_title(person, wiki)
    if source_title:
        return source_title
    if valid_title(old) and "太子" not in old:
        exact = candidates(old)
        return min(exact, key=lambda item: title_score(item, person.get("category", ""))) if exact else old
    return ""


def display_name(person: dict, wiki: str) -> str:
    if person.get("category") == "宗藩" and person["name"].endswith("公主"):
        match = DISPLAY_NAME.search(f"{person.get('summary', '')}\n{wiki[:1200]}")
        if match:
            return match.group(1)
    return person["name"]


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


def finalize(apply: bool) -> tuple[int, list[str]]:
    names = [
        "person_category", "person_section_definition", "person", "person_wiki", "person_mingshi",
        "person_section", "content_reference",
    ]
    tables = {name: load(name) for name in names}
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
        person["title"] = canonical_title(person, full_text)
        person["display_name"] = display_name(person, full_text)
        if person["id"] in EMPEROR_TITLES or CROWN.search(person["title"]):
            person["category"] = "帝王"
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

    if unresolved:
        return len(tables["person"]), sorted(set(unresolved))
    if apply:
        for name in ("person", "person_section"):
            dump(name, tables[name])
    return len(tables["person"]), []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    count, unresolved = finalize(args.apply)
    if unresolved:
        raise SystemExit("人物正式库未完成：\n" + "\n".join(unresolved[:80]) + ("\n……" if len(unresolved) > 80 else ""))
    print(f"人物正式库已通过：{count} 人")


if __name__ == "__main__":
    main()
