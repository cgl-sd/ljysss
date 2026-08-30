#!/usr/bin/env python3
"""统一清洗并审计人物介绍的正文、分类与分栏。

人物详情的来源正文一律取自 ``person_wiki.full_text``，而不是早期拼接后可能混入
消歧义项、分类标签或参考文献的 ``person_section``。本脚本只使用可复核的通用规则：

* 删除空的中英文括号、维基脚注、参考文献尾部、分类/科举标签和名片式元数据；
* 保留维基正文中真实存在的小标题；超长且无小标题时统一补“概览／纪事”，不生成
  与外层“生平”重复的标题；
* 保留一份去重后的 ``〔《明史》原文〕`` 块；
* 校验六分类、四分栏、中文维基人物页及来源登记；
* 对简介明确称为“明朝军事将领”的人物，以同一条通用规则归入“将帅”。

    backend/.venv/bin/python backend/scripts/normalize_person_profiles.py --check
    backend/.venv/bin/python backend/scripts/normalize_person_profiles.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
CONTENT = BACKEND / "data" / "content"
DEFAULT_REPORT = ROOT / "tmp" / "person-profile-audit.json"

MINGSHI_MARKER = "〔《明史》原文〕"
EMPTY_PARENS = re.compile(r"[（(]\s*[）)]")
WIKI_FOOTNOTE = re.compile(r"\[(?:\d+|註?\s*\d+|[a-zA-Z])\]")
WIKI_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}|<[^>]*>")
REFERENCE_HEADING = re.compile(
    r"^(?:参考文献|参考资料|參考文獻|參考資料|注释|注釋|备注|備註|外部链接|外部連結|"
    r"参见|參見|延伸阅读|延伸閱讀|书目|書目|参考书目|參考書目|参考|參考|引用|来源|來源)(?:[：:].*)?$"
)
META_LINE = re.compile(
    r"^(?:本名|别名|別名|全名|字|号|號|尊号|尊號|庙号|廟號|谥号|諡號|追赠|追贈|"
    r"封号|封號|年号|年號|政权|政權|民族族群|信仰|王朝|所处时代|所處時代|出生地|"
    r"出生日期|逝世日期|逝世地|陵墓|安葬地|在位时间|在位時間|前任|继任|繼任|继承者|"
    r"主要成就|主要作品|最高官职|最高官職|重要事件|相关人物|相關人物|墓地|墓葬|亲属|"
    r"親屬|爵位|位号|位號|封地)[：:]"
)
FAMILY_HEADING = re.compile(r"^(?:家族|家庭|子嗣|親屬|亲属|后裔|後裔|世系|婚姻|父母|兄弟|姐妹|子女|配偶)$")
DROP_HEADING = re.compile(
    r"^(?:影视|影視|艺术形象|藝術形象|流行文化|衍生作品|评价|評價|影响|影響|纪念|紀念|"
    r"争议|爭議|轶事|軼事|相关条目|相關條目|著作|作品|学术|學術|思想|学术思想|學術思想|年号|年號)$"
)
REGNAL_EXAM_LINE = re.compile(
    r"^(?:至正|洪武|建文|永乐|永樂|洪熙|宣德|正统|正統|景泰|天顺|天順|成化|弘治|"
    r"正德|嘉靖|隆庆|隆慶|万历|萬曆|泰昌|天启|天啟|崇祯|崇禎|弘光|隆武|绍武|紹武|"
    r"永历|永曆).{0,20}(?:举人|舉人|进士|進士)$"
)
CATEGORY_LINE = re.compile(
    r"^(?:明(?:朝|代|初|末).{0,28}(?:官员|官員|政治人物|将领|將領|军事人物|軍事人物|"
    r"诗人|詩人|作家|画家|畫家|书法家|書法家|学者|學者|医家|醫家|僧人|进士|進士|"
    r"公主|皇女|宗室|侯爵|伯爵)|[A-Z][A-Za-z0-9 _-]{0,12}|《明史[·・].*》)$"
)
DISAMBIGUATION = re.compile(r"(?:可指|可以指|可能是指|下列.*?(?:名字为|人物|公主)|数个名为|可指下列人物)")
PLACEHOLDER = re.compile(r"^(?:其家世与亲属，)?(?:现存史料|現存史料|资料|資料)未见详载。?$", re.I)
LONG_BIO_WITHOUT_HEADINGS = 900

LITERARY = re.compile(r"诗人|詩人|文学家|文學家|文人|学者|學者|画家|畫家|书法家|書法家|医家|醫家|医学家|醫學家|艺术家|藝術家|戏曲家|戲曲家")
OFFICIAL = re.compile(r"官员|官員|政治人物|官吏|进士|進士|尚书|尚書|侍郎|御史|知县|知縣|主事|给事中|給事中|大学士|大學士|翰林")
MING_CONTEXT = r"(?:元末明初|南明|明(?:朝|代|初|末))"
DIRECT_MILITARY = re.compile(
    MING_CONTEXT + r"[^。！？\n]{0,24}(?:军事将领|軍事將領|军事人物|軍事人物|将领|將領|名将|名將|武将|武將|开国功臣|開國功臣)"
)
DIRECT_LITERARY = re.compile(
    MING_CONTEXT + r"[^。！？\n]{0,24}(?:文学家|文學家|诗人|詩人|文人|戏曲家|戲曲家|画家|畫家|书法家|書法家|学者|學者|医家|醫家)"
)
DIRECT_OFFICIAL = re.compile(
    MING_CONTEXT + r"[^。！？\n]{0,24}(?:官员|官員|政治人物|官吏)"
)


def load(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(table: str, rows: list[dict]) -> None:
    path = CONTENT / f"{table}.jsonl"
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def normalize_line(raw: str) -> str:
    line = WIKI_TEMPLATE.sub("", WIKI_FOOTNOTE.sub("", raw or "")).strip()
    # 空括号有时原本隔开姓名与“明朝……”，先在仍能识别括号时补回句读。
    line = re.sub(r"([\u4e00-\u9fff])\s*[（(]\s*[）)]\s*(?=明(?:朝|代))", r"\1，", line)
    line = EMPTY_PARENS.sub("", line)
    line = re.sub(r"([，,、])\s*(?:[，,、]\s*)+", r"\1", line)
    return re.sub(r"\s+", " ", line).strip(" ")


def is_heading(line: str) -> bool:
    return bool(line) and len(line) <= 18 and not re.search(r"[。！？；：，,]", line)


def is_noise_line(line: str) -> bool:
    return bool(
        not line
        or META_LINE.match(line)
        or REGNAL_EXAM_LINE.match(line)
        or CATEGORY_LINE.match(line)
        or re.fullmatch(r"[\d０-９]+", line)
        or (len(line) <= 4 and re.fullmatch(r"[A-Z][A-Za-z0-9 _-]*", line))
    )


def sentence_chunks(text: str, limit: int = 260) -> list[str]:
    """以句读为边界切短段，作为无原始小标题的长文的通用移动端排版。"""

    sentences = [part.strip() for part in re.split(r"(?<=[。！？；])", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) > limit:
            chunks.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        chunks.append(current)
    return chunks or [text]


def add_long_bio_structure(lines: list[str]) -> list[str]:
    """仅对无原始小标题的超长正文补“概览／纪事”，不依赖具体人物。"""

    if any(is_heading(line) for line in lines) or sum(map(len, lines)) < LONG_BIO_WITHOUT_HEADINGS:
        return lines
    chunks = sentence_chunks("".join(lines))
    if len(chunks) < 2:
        return lines
    overview = chunks[0]
    remaining = chunks[1:]
    return ["概览", overview, "纪事", *remaining]


def clean_wikipedia_bio(raw: str) -> str:
    """保留人物叙事与既有小标题，去除维基结构噪音；不生成任何人物专属标题。"""

    kept: list[str] = []
    in_family = False
    skip_section = False
    stop = False
    for original in (raw or "").replace("\r", "").split("\n"):
        line = normalize_line(original)
        if not line or stop:
            continue
        if REFERENCE_HEADING.match(line):
            stop = True
            continue
        if FAMILY_HEADING.match(line):
            in_family = True
            skip_section = False
            continue
        # 维基导出的分类、科举标签和语言代码多数是短行，不能先被当作小标题保留。
        if is_noise_line(line):
            continue
        if is_heading(line):
            if line == "生平":
                # 维基常把“家族”置于“生平”之前；这里恢复叙事收集，而不是把
                # 后续生平误当作家庭资料一并丢弃。
                in_family = False
                skip_section = False
                continue
            if DROP_HEADING.match(line):
                in_family = False
                skip_section = True
                continue
            in_family = False
            skip_section = False
            if kept and kept[-1] == line:
                continue
            kept.append(line)
            continue
        if in_family or skip_section:
            continue
        kept.append(line)
    return "\n\n".join(add_long_bio_structure(kept)).strip()


def extract_mingshi_block(content: str) -> str:
    """保留最长的一份明史原文，消除早期导入造成的重复块。"""

    if MINGSHI_MARKER not in (content or ""):
        return ""
    candidates = [part.strip() for part in content.split(MINGSHI_MARKER)[1:] if len(part.strip()) >= 16]
    if not candidates:
        return ""
    return MINGSHI_MARKER + "\n" + max(dict.fromkeys(candidates), key=len)


def modern_life(content: str) -> str:
    return (content or "").split(MINGSHI_MARKER, 1)[0].strip()


def has_wikipedia_reference(refs: list[dict], person_id: str) -> bool:
    return any(
        row.get("content_type") == "person"
        and row.get("content_id") == person_id
        and urlparse(row.get("url", "")).netloc == "zh.wikipedia.org"
        for row in refs
    )


def is_disambiguation(text: str) -> bool:
    head = "\n".join(line.strip() for line in (text or "").splitlines() if line.strip())[:240]
    return bool(DISAMBIGUATION.search(head))


def inferred_category(person: dict, wiki_text: str) -> str:
    """按维基导语与现有称号重算六分类；证据不足时保留既有类别而不猜测。"""

    intro_parts: list[str] = []
    for line in (wiki_text or "").splitlines():
        line = normalize_line(line)
        if not line:
            continue
        if intro_parts and is_heading(line):
            break
        intro_parts.append(line)
        if len("".join(intro_parts)) >= 360:
            break
    intro = "".join(intro_parts)[:360]
    title = person.get("title", "")
    # 君主、内廷与宗室只能由条目称号确认；导语经常会提及传主的君主、父母或同僚，
    # 不能把这些身份误归给传主。其余类别须有导语的明朝身份词或称号证据，证据不足
    # 时保留现有类别而不猜测。
    if re.search(r"皇帝|监国|監國|君主|[\u4e00-\u9fff]帝(?:[、·]|$)", title):
        return "帝王"
    if re.search(r"皇后|太后|贵妃|貴妃|淑妃|贤妃|賢妃|嫔|嬪|宦官|太监|太監", title):
        return "内廷"
    if re.search(r"公主|宗室|亲王|親王|郡王|藩王|世子|皇子|皇女|(?:^|[、·])[^、·]{1,5}王(?:[、·]|$)", title):
        return "封爵"
    if re.search(r"将领|將領|名将|名將|武将|武將|总兵|總兵|都督|指挥使|指揮使", title):
        return "将帅"
    if DIRECT_MILITARY.search(intro):
        return "将帅"
    if DIRECT_LITERARY.search(intro):
        return "文苑"
    if DIRECT_OFFICIAL.search(intro):
        return "朝臣"
    if LITERARY.search(title):
        return "文苑"
    if re.search(r"国公|國公|侯爵|伯爵|勋贵|勳貴", title):
        return "封爵"
    if OFFICIAL.search(title):
        return "朝臣"
    return person.get("category", "")


def category_is_compatible(person: dict, wiki_text: str) -> bool:
    return person.get("category") == inferred_category(person, wiki_text)


def normalize_tables(tables: dict[str, list[dict]]) -> dict[str, int]:
    wiki_by_id = {row["person_id"]: row for row in tables["person_wiki"]}
    lives = {row["person_id"]: row for row in tables["person_section"] if row["section_key"] == "life"}
    stats: Counter[str] = Counter()

    for person in tables["person"]:
        person_id = person["id"]
        wiki = wiki_by_id.get(person_id, {})
        body = clean_wikipedia_bio(wiki.get("full_text", ""))
        old = lives.get(person_id, {}).get("content", "")
        block = extract_mingshi_block(old)
        content = body + ("\n\n" + block if body and block else block)
        lives[person_id] = {
            "person_id": person_id,
            "section_key": "life",
            "title": "生平",
            "position": 0,
            "content": content,
        }
        person["biography"] = body
        person["summary"] = re.sub(r"\s+", " ", body)[:120]
        inferred = inferred_category(person, wiki.get("full_text", ""))
        if inferred != person["category"]:
            person["category"] = inferred
            stats["categories_reclassified"] += 1
        if content != old:
            stats["life_normalized"] += 1

    tables["person_section"] = [
        row for row in tables["person_section"]
        if row["section_key"] != "life"
        and not (
            row["section_key"] == "family"
            and (not row["content"].strip() or PLACEHOLDER.match(row["content"].strip()))
        )
    ]
    tables["person_section"].extend(lives.values())
    family_ids = {row["person_id"] for row in tables["person_section"] if row["section_key"] == "family"}
    for person in tables["person"]:
        if person["id"] not in family_ids and PLACEHOLDER.match(person.get("family_summary", "").strip()):
            person["family_summary"] = ""
            stats["family_placeholders_removed"] += 1
    return dict(stats)


def audit_tables(tables: dict[str, list[dict]]) -> dict:
    categories = {row["label"] for row in tables["person_category"]}
    definitions = {
        row["section_key"]: (row["title"], row["position"])
        for row in tables["person_section_definition"]
    }
    people = {row["id"]: row for row in tables["person"]}
    wiki = {row["person_id"]: row for row in tables["person_wiki"]}
    sections: dict[str, list[dict]] = {}
    for row in tables["person_section"]:
        sections.setdefault(row["person_id"], []).append(row)

    problems: list[dict] = []
    for person_id, person in people.items():
        source = wiki.get(person_id, {})
        source_text = source.get("full_text", "")
        rows = {row["section_key"]: row for row in sections.get(person_id, [])}
        life = rows.get("life", {})
        body = modern_life(life.get("content", ""))
        reasons: list[str] = []
        if person.get("category") not in categories:
            reasons.append("分类不在六分类目录")
        elif not category_is_compatible(person, source_text):
            reasons.append("分类与维基身份词不相容")
        if not source_text or is_disambiguation(source_text):
            reasons.append("维基正文缺失或是消歧页")
        if not has_wikipedia_reference(tables["content_reference"], person_id):
            reasons.append("缺少中文维基出处登记")
        if not body:
            reasons.append("生平无可展示叙事正文")
        if EMPTY_PARENS.search(body):
            reasons.append("生平仍含空括号")
        for line in body.splitlines():
            line = line.strip()
            if line and (REFERENCE_HEADING.match(line) or is_noise_line(line)):
                reasons.append("生平仍含参考或分类短行")
                break
        for key, row in rows.items():
            expected = definitions.get(key)
            if not expected or (row.get("title"), row.get("position")) != expected:
                reasons.append("分栏键、标题或排序不合法")
            if not row.get("content", "").strip() or PLACEHOLDER.match(row.get("content", "").strip()):
                reasons.append("分栏为空或为占位文案")
        if reasons:
            problems.append({"id": person_id, "name": person["name"], "problems": sorted(set(reasons))})

    return {
        "people": len(people),
        "categories": len(categories),
        "section_definitions": len(definitions),
        "valid": len(people) - len(problems),
        "invalid": len(problems),
        "problems": problems,
    }


def main(apply: bool, report: Path) -> None:
    names = [
        "person_category", "person_section_definition", "person", "person_wiki",
        "person_section", "content_reference",
    ]
    tables = {name: load(name) for name in names}
    stats = normalize_tables(tables) if apply else {}
    result = audit_tables(tables)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"summary": result, "changes": stats}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"人物介绍审计：人物 {result['people']}｜分类 {result['categories']}｜栏目 {result['section_definitions']}｜"
        f"通过 {result['valid']}｜问题 {result['invalid']}"
    )
    print(f"报告：{report}")
    if result["problems"]:
        examples = "；".join(f"{row['name']}（{'、'.join(row['problems'])}）" for row in result["problems"][:12])
        raise SystemExit(f"人物介绍未通过校验：{examples}")
    if apply:
        for name, rows in tables.items():
            dump(name, rows)
        print("已写入清洗后的生平、人物摘要与分类。" + "｜".join(f"{key} {value}" for key, value in stats.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="通过校验后写回 data/content/*.jsonl")
    parser.add_argument("--check", action="store_true", help="只审计当前内容（默认）")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    main(apply=args.apply, report=args.report)
