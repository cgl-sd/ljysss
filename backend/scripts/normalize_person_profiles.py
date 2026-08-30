#!/usr/bin/env python3
"""统一清洗并审计人物介绍的正文、分类与分栏。

人物详情的来源正文一律取自 ``person_wiki.full_text``，而不是早期拼接后可能混入
消歧义项、分类标签或参考文献的 ``person_section``。本脚本只使用可复核的通用规则：

* 删除空的中英文括号、维基脚注、参考文献尾部、分类/科举标签和名片式元数据；
* 保留维基正文中真实存在的小标题；超长且无小标题时统一补“概览／纪事”，不生成
  与外层“生平”重复的标题；
* 保留一份去重后的 ``〔《明史》原文〕`` 块；
* 校验六分类、四分栏、中文维基人物页及来源登记；
* 分类只依据传主自己的称号与维基导语：内廷限后妃、宫人、乳母与宦官；宗藩限
  皇室宗亲与藩王；任高阶官职的文人归入朝臣而非文苑；
* 爵位不是分类依据：有军事或政务角色的勋贵分别归入将帅或朝臣。

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

from opencc import OpenCC

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
CONTENT = BACKEND / "data" / "content"
DEFAULT_REPORT = ROOT / "tmp" / "person-profile-audit.json"

MINGSHI_MARKER = "〔《明史》原文〕"
T2S = OpenCC("t2s")
# “乾清宫”在简体中文中仍写作“乾”，不能按通用字形转换为“干”。
SIMPLIFIED_PROPER_NOUNS = {"乾清宫": "__QIANQING_PALACE__"}
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
# 这些模式是这轮 AI 语义审校落地后的公开规则：不是因为“字数短”就当标题，而是
# 按栏目语义区分叙事、家族和作品/评价等资料。原始《明史》块不经过此规则。
FAMILY_HEADING = re.compile(
    r"^(?:(?:家族|家庭|家世|家系|家人|亲属|后裔|世系|婚姻|父母|兄弟|姐妹|子女|儿女|"
    r"儿子|女儿|配偶|妻妾|个人生活)(?:成员|背景|及关联|与子嗣|与家庭)?|子嗣|父亲|母亲|"
    r"兄弟姊妹|妻|妾|夫人|丈夫|子|女|孙|伯父|叔父)$"
)
NON_NARRATIVE_HEADING = re.compile(
    r"(?:影视|电影|电视剧|戏剧|戏曲|动画|漫画|游戏|艺术形象|流行文化|文学形象|"
    r"衍生作品|著作|著述|作品|诗作|诗文|诗歌|书画|书法|绘画|画作|艺术|文学|文化|"
    r"学术|思想|信仰|宗教|评价|评论|影响|地位|成就|纪念|争议|传说|轶事|逸事|"
    r"遗迹|遗物|故居|墓葬|陵墓|圹志|墓志|身后|后世|相关条目|其他|简介|注释|"
    r"脚注|参考|书目|外部|参看|參看|註釋|个性|個性|年号|年號|绝命辞|绝命诗|诗词|词作|对句)"
)
NARRATIVE_HEADING = re.compile(
    r"^(?:概览|纪事|早年(?:经历|生涯)?|早期(?:经历|生涯)?|晚年(?:经历|生涯)?|求学|仕途|仕宦|从政|入仕|"
    r"经历|事迹|生涯|官宦|军旅|征战|战事|戍边|任职|政绩|为政举措|即位|登基|驾崩|"
    r"去世|逝世|殉国|遗诏|后事|身世|大礼议|靖难之役|国本之争|夺门之变|土木堡之变|"
    r"弘治朝|正德朝|世宗朝|万历朝|天启朝|崇祯朝|"
    r"(?:至正|洪武|建文|永乐|洪熙|宣德|正统|景泰|天顺|成化|弘治|正德|嘉靖|隆庆|"
    r"万历|泰昌|天启|崇祯|弘光|隆武|绍武|永历)[、，,及和与—\-]*(?:至正|洪武|建文|"
    r"永乐|洪熙|宣德|正统|景泰|天顺|成化|弘治|正德|嘉靖|隆庆|万历|泰昌|天启|崇祯|"
    r"弘光|隆武|绍武|永历)?年间)$"
)
FAMILY_SENTENCE_PREFIX = re.compile(
    r"^(?:其|他的|她的)?(?:父|父亲|母|母亲|祖父|祖母|曾祖|兄|弟|姐|妹|子|女|儿子|女儿|"
    r"孙|配偶|妻|妻子|夫人|妾|丈夫|家人|家族|家庭|子嗣|后代|后裔)(?:[：:,，、]|是|为|有)"
)
FAMILY_SENTENCE_LIST = re.compile(
    r"(?:育有|生有|有[一二三四五六七八九十\d]+子|有子女|子女(?:有|为)|儿女(?:有|为)|"
    r"子女出生|儿子|女儿|子嗣(?!位)|妻妾|配偶(?:为|是|有)|家族成员|家庭成员|父母兄弟|兄弟姐妹|子孙|"
    r"第[一二三四五六七八九十\d]+[子女]|(?:嫡|庶|长|次|幼|独)[子女]|之(?:父|母|子|女|孙|祖父|祖母|兄|弟|姐|妹|妻|夫)|"
    r"国丈|外祖父|岳父|女婿|外孙|先人|祖先|家族|家世)"
)
FAMILY_MEMBER_WORD = re.compile(
    r"(?:父亲|母亲|父母|祖父|祖母|曾祖父|曾祖母|兄弟|姐妹|弟弟|哥哥|姐姐|妹妹|儿子|女儿|"
    r"子嗣|后代|后裔|妻子|夫人|配偶|妻妾)"
)
WORK_SENTENCE = re.compile(
    r"(?:影视|电影|电视剧|戏剧|戏曲|动画|漫画|游戏|著有|著作(?:有|包括)|代表作|作品(?:有|包括|为)|"
    r"著作|著述|绘画作品|书法作品|画作|书画作品|诗作|诗集|作品|出演|饰演|扮演|艺术形象|文学形象)"
)
EVALUATION_SENTENCE = re.compile(r"(?:人物评价|历史评价|正面评价|负面评价|后世评价|被[^。！？；]{0,16}誉为|被[^。！？；]{0,16}譽為|影响深远|影響深遠|史学界.*争议|史學界.*爭議|存在较大的争议|存在較大的爭議)")
SEE_ALSO_LINE = re.compile(r"^[（(]?(?:参看|另见|主条目|参见).*[）)]?$")
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
CATEGORY_TAIL = re.compile(
    r"[，,]?(?:明(?:朝|代|初|末).{0,28}(?:官员|政治人物|将领|军事人物|诗人|作家|画家|书法家|学者|医家|僧人|进士|公主|皇女|宗室|侯爵|伯爵))$"
)
DISAMBIGUATION = re.compile(r"(?:可指|可以指|可能是指|下列.*?(?:名字为|人物|公主)|数个名为|可指下列人物)")
PLACEHOLDER = re.compile(r"^(?:其家世与亲属，)?(?:现存史料|現存史料|资料|資料)未见详载。?$", re.I)
LONG_BIO_WITHOUT_HEADINGS = 900

LITERARY = re.compile(r"诗人|詩人|文学家|文學家|文人|作家|學者|学者|画家|畫家|书法家|書法家|医家|醫家|医学家|醫學家|艺术家|藝術家|戏曲家|戲曲家|戏曲作家|戲曲作家")
OFFICIAL = re.compile(r"官员|官員|政治人物|官吏|进士|進士|尚书|尚書|侍郎|御史|知县|知縣|主事|给事中|給事中|大学士|大學士|翰林")
# “当过大官”须压过文人身份。进士、主事等一般仕履不单独否定文苑，避免把以
# 文化成就为主、短暂任低阶职的人一律挪走。
SENIOR_CIVIL_OFFICE = re.compile(
    r"内阁|內閣|大学士|大學士|首辅|首輔|尚书|尚書|侍郎|都御史|巡抚|巡撫|总督|總督|"
    r"布政使|按察使|大理寺[卿丞]|通政使|詹事|祭酒|太子太保|太子少保|少师|少傅|少保|"
    r"六部(?:尚书|侍郎)|南京(?:吏|户|礼|兵|刑|工)部"
)
INNER_COURT_IDENTITY = re.compile(
    r"皇后|太后|太皇太后|皇贵妃|皇貴妃|贵妃|貴妃|淑妃|贤妃|賢妃|妃|嫔|嬪|"
    r"选侍|選侍|宦官|太监|太監|内官|內官|宫人|宮人|女官|乳母|奉圣夫人|奉聖夫人"
)
GENERIC_INNER_COURT_TITLE = re.compile(r"^(?:宦官|后妃)$")
DIRECT_INNER_COURT = re.compile(
    r"(?:元末明初|南明|明(?:朝|代|初|末))[^。！？\n]{0,24}(?:宦官|太监|太監|内官|內官|皇后|太后|贵妃|貴妃|妃|嫔|嬪|选侍|選侍|宫人|宮人|乳母)"
)
IMPERIAL_CLAN_IDENTITY = re.compile(
    r"皇太子|皇子|皇女|公主|宗室|宗亲|宗親|藩王|亲王|親王|郡王|世子|郡主|"
    r"(?:^|[、，,／/·])[^、，,／/·]{1,5}王(?:[、，,／/]|$)"
)
GENERIC_CLAN_TITLE = re.compile(r"^明(?:朝|代)?藩王$")
DIRECT_IMPERIAL_CLAN = re.compile(
    r"(?:元末明初|南明|明(?:朝|代|初|末))[^。！？\n]{0,32}(?:宗室|宗亲|宗親|藩王|亲王|親王|郡王|公主|皇太子|皇子|皇女)"
)
IMPERIAL_LINEAGE_IN_INTRO = re.compile(
    r"(?:^[^。！？]{0,18}王朱|明(?:太祖|成祖|仁宗|宣宗|英宗|代宗|宪宗|孝宗|武宗|世宗|穆宗|神宗|光宗|熹宗|思宗)"
    r"[^。！？]{0,28}第[一二三四五六七八九十\d]+(?:子|女)|明朝第[一二三四五六七八九十\d]+代[^。！？]{0,10}王)"
)
MING_CONTEXT = r"(?:元末明初|南明|明(?:朝|代|初|末))"
DIRECT_MILITARY = re.compile(
    MING_CONTEXT + r"[^。！？\n]{0,24}(?:军事将领|軍事將領|军事人物|軍事人物|将领|將領|名将|名將|武将|武將|开国功臣|開國功臣)"
)
DIRECT_LITERARY = re.compile(
    MING_CONTEXT + r"[^。！？\n]{0,24}(?:文学家|文學家|诗人|詩人|文人|作家|戏曲家|戲曲家|戏曲作家|戲曲作家|画家|畫家|书法家|書法家|学者|學者|医家|醫家)"
)
DIRECT_OFFICIAL = re.compile(
    MING_CONTEXT + r"[^。！？\n]{0,24}(?:官员|官員|政治人物|官吏)"
)
MILITARY_OFFICE = re.compile(r"总兵|總兵|副总兵|副總兵|参将|參將|游击|遊擊|都督|都指挥|都指揮|指挥使|指揮使|守备|守備")


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
    line = simplify_modern_text(WIKI_TEMPLATE.sub("", WIKI_FOOTNOTE.sub("", raw or "")).strip())
    line = re.sub(r"[（(](?:参看|另见|主条目|参见)[^）)]*[）)]", "", line)
    # 空括号有时原本隔开姓名与“明朝……”，先在仍能识别括号时补回句读。
    line = re.sub(r"([\u4e00-\u9fff])\s*[（(]\s*[）)]\s*(?=明(?:朝|代))", r"\1，", line)
    line = EMPTY_PARENS.sub("", line)
    line = re.sub(r"([，,、])\s*(?:[，,、]\s*)+", r"\1", line)
    return re.sub(r"\s+", " ", line).strip(" ")


def simplify_modern_text(text: str) -> str:
    """统一现代说明文字为简体，同时保护简体中沿用的专名。"""

    for proper_noun, token in SIMPLIFIED_PROPER_NOUNS.items():
        text = text.replace(proper_noun, token)
    text = T2S.convert(text)
    for proper_noun, token in SIMPLIFIED_PROPER_NOUNS.items():
        text = text.replace(token, proper_noun)
    return text


def is_heading(line: str) -> bool:
    return bool(line) and len(line) <= 18 and not re.search(r"[。！？；：，,]", line)


def is_section_label(line: str) -> bool:
    """维基小标题有时超过 UI 的标题阈值，仍须用于判断应跳过的资料分栏。"""

    return bool(line) and len(line) <= 42 and not re.search(r"[。！？；：，,]", line)


def is_non_narrative_section_label(line: str) -> bool:
    # 只把真正的短行标题当作分栏；叙事句中出现“影响”“思想”等词不能误删。
    return is_heading(line) and bool(NON_NARRATIVE_HEADING.search(line))


def starts_non_narrative_section(line: str) -> bool:
    """少数维基把“关于……争议中，……”与正文写在同一行，仍视作整段资料。"""

    return bool(re.match(r"^关于.{0,30}(?:争议|评价|影响).{0,4}(?:中)?(?=[，,:])", line))


def is_narrative_heading(line: str) -> bool:
    """只有时间/经历类小标题可在生平中以深色标题显示。"""

    return bool(NARRATIVE_HEADING.fullmatch(line))


def is_family_sentence(sentence: str) -> bool:
    """只删名录式亲属资料；传主导语中的单一亲属身份不会误删。"""

    return bool(
        FAMILY_SENTENCE_PREFIX.match(sentence)
        or FAMILY_SENTENCE_LIST.search(sentence)
        or len(FAMILY_MEMBER_WORD.findall(sentence)) >= 3
    )


def is_family_clause(clause: str) -> bool:
    """识别句内的亲属名录子句，以便删去家族信息而尽量留下同句的生平事实。"""

    return bool(
        FAMILY_SENTENCE_PREFIX.match(clause)
        or FAMILY_SENTENCE_LIST.search(clause)
        or FAMILY_MEMBER_WORD.search(clause)
    )


def remove_family_clauses(sentence: str) -> str:
    clauses = re.split(r"(?<=[，,；])", sentence)
    kept = [clause for clause in clauses if clause.strip() and not is_family_clause(clause)]
    return "".join(kept).strip(" ，,；")


def remove_inline_evaluation(sentence: str) -> str:
    """导语中的“被誉为……”只去掉评价尾语，保留姓名、身份等基础介绍。"""

    return re.sub(r"[，,]?被[^。！？；]{0,16}(?:誉为|譽為)[^。！？；]*", "", sentence).strip()


def semantic_sentences(line: str, stats: Counter[str] | None = None) -> list[str]:
    """以叙事语义审阅一段正文，删除混入段内的家族、作品和评价句。"""

    kept: list[str] = []
    for sentence in (part.strip() for part in re.split(r"(?<=[。！？；])", line) if part.strip()):
        if is_family_sentence(sentence):
            without_family = remove_family_clauses(sentence)
            if without_family:
                sentence = without_family
                if stats is not None:
                    stats["family_clauses_removed"] += 1
            else:
                if stats is not None:
                    stats["family_sentences_removed"] += 1
                continue
        if WORK_SENTENCE.search(sentence):
            if stats is not None:
                stats["works_sentences_removed"] += 1
            continue
        if EVALUATION_SENTENCE.search(sentence):
            without_evaluation = remove_inline_evaluation(sentence)
            if without_evaluation and without_evaluation != sentence:
                sentence = without_evaluation
                if stats is not None:
                    stats["evaluation_clauses_removed"] += 1
            else:
                if stats is not None:
                    stats["evaluation_sentences_removed"] += 1
                continue
        kept.append(sentence)
    return kept


def is_noise_line(line: str) -> bool:
    return bool(
        not line
        or META_LINE.match(line)
        or SEE_ALSO_LINE.match(line)
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


def clean_wikipedia_bio(raw: str, stats: Counter[str] | None = None) -> str:
    """以生平叙事为准清洗维基正文，拒绝家族、作品、评价等非生平材料。"""

    kept: list[str] = []
    section_mode = "narrative"
    stop = False
    for original in (raw or "").replace("\r", "").split("\n"):
        line = normalize_line(original)
        if not line or stop:
            continue
        if REFERENCE_HEADING.match(line):
            stop = True
            continue
        if FAMILY_HEADING.match(line):
            section_mode = "family"
            if stats is not None:
                stats["family_sections_removed"] += 1
            continue
        # 维基导出的分类、科举标签和语言代码多数是短行，不能先被当作小标题保留。
        if is_noise_line(line):
            continue
        if is_non_narrative_section_label(line) or starts_non_narrative_section(line):
            section_mode = "non_narrative"
            if stats is not None:
                stats["non_narrative_sections_removed"] += 1
            continue
        if is_heading(line):
            if line == "生平":
                section_mode = "narrative"
                continue
            if section_mode != "narrative":
                # 家族/作品分栏内的“子”“电视剧”等子标题不重新开启生平。
                if is_narrative_heading(line):
                    section_mode = "narrative"
                else:
                    continue
            if is_narrative_heading(line):
                if not kept or kept[-1] != line:
                    kept.append(line)
            continue
        if section_mode != "narrative":
            continue
        for sentence in semantic_sentences(line, stats):
            sentence = CATEGORY_TAIL.sub("", sentence).strip(" ，,；")
            # 删除句内家族子句后，剩下的“明朝政治人物”等分类短语也不可成为正文。
            if sentence and not is_noise_line(sentence):
                kept.append(sentence)
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


def person_intro(wiki_text: str) -> str:
    """取维基导语；只用传主身份最集中的开头，避免正文他人身份造成误归。"""

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
    return "".join(intro_parts)[:360]


def is_inner_court_identity(title: str, intro: str) -> bool:
    """内廷只接受传主本人明确的宫廷身份，不能由正文中的大臣或皇帝反推。"""

    # 早期导入曾把崔铣、梁寅等称号粗写为“宦官”。具体宫廷称号可直接采用；
    # 裸“宦官/后妃”须由维基导语确认，不能让错误旧标签把大臣留在内廷。
    if GENERIC_INNER_COURT_TITLE.fullmatch(title):
        return bool(DIRECT_INNER_COURT.search(intro[:180]))
    return bool(INNER_COURT_IDENTITY.search(title))


def is_imperial_clan_identity(title: str, intro: str) -> bool:
    """宗藩按血缘/藩王身份，而非“国公、侯、伯”等可获得的爵位判断。"""

    # 早期导入将少量人物的称号粗写成“明朝藩王”；这类泛称会把陈奇瑜、张凤翼
    # 等传主错分，故必须再由维基导语确认。具体王号、世子、公主等则可直接确认。
    head = re.split(r"[。！？]", intro, maxsplit=1)[0]
    return bool(
        (not GENERIC_CLAN_TITLE.fullmatch(title) and IMPERIAL_CLAN_IDENTITY.search(title))
        or DIRECT_IMPERIAL_CLAN.search(intro[:180])
        or IMPERIAL_LINEAGE_IN_INTRO.search(head)
    )


def inferred_category(person: dict, wiki_text: str) -> str:
    """按传主称号与维基导语重算六分类，爵位本身不再构成一类。"""

    intro = person_intro(wiki_text)
    title = person.get("title", "")
    # 君主、内廷与宗藩只能由条目称号或导语的传主身份确认；正文经常提及其君主、
    # 父母和同僚，不能从这些他人身份反推分类。
    if (
        re.search(r"皇帝|监国|監國|君主|[\u4e00-\u9fff]帝(?:[、·]|$)", title)
        or re.search(r"(?:自称|自稱|称|稱)(?:为|為)?(?:监国|監國)", intro[:180])
    ):
        return "帝王"
    if is_inner_court_identity(title, intro):
        return "内廷"
    if is_imperial_clan_identity(title, intro):
        return "宗藩"
    if re.search(r"将领|將領|名将|名將|武将|武將|总兵|總兵|都督|指挥使|指揮使", title):
        return "将帅"
    if DIRECT_MILITARY.search(intro) or MILITARY_OFFICE.search(intro):
        return "将帅"
    if SENIOR_CIVIL_OFFICE.search(title) or SENIOR_CIVIL_OFFICE.search(intro):
        return "朝臣"
    if DIRECT_LITERARY.search(intro):
        return "文苑"
    if LITERARY.search(title):
        return "文苑"
    if DIRECT_OFFICIAL.search(intro):
        return "朝臣"
    if OFFICIAL.search(title):
        return "朝臣"
    # 勋贵不再按爵位单列；来源未提供可复核的新身份词时仅保留已有职业类别，
    # 避免把原有将帅、文苑因导语过短而错误冲掉。
    previous = person.get("category", "")
    # 帝王、内廷、宗藩都必须每次由正面身份证据确认；不能因旧导入标签而留存。
    return previous if previous in {"朝臣", "将帅", "文苑"} else "朝臣"


def category_is_compatible(person: dict, wiki_text: str) -> bool:
    return person.get("category") == inferred_category(person, wiki_text)


PERSON_CATEGORY_REGISTRY = (
    ("emperor", "帝王", 0, "在位君主与南明监国。"),
    ("inner-court", "内廷", 1, "宫中的后妃、宫人、乳母与宦官。"),
    ("imperial-clan", "宗藩", 2, "皇室宗亲、藩王与公主；不以爵位作为归类理由。"),
    ("official", "朝臣", 3, "参与中枢、地方或朝廷政治的非军事人物。"),
    ("general", "将帅", 4, "统兵将领与其他以军事活动为主的人物。"),
    ("literary", "文苑", 5, "未任高阶官职、以文艺、学术、医术等成就为主的人物。"),
)


def normalize_category_registry(tables: dict[str, list[dict]]) -> None:
    tables["person_category"] = [
        {"id": category_id, "label": label, "position": position, "description": description}
        for category_id, label, position, description in PERSON_CATEGORY_REGISTRY
    ]


def normalize_tables(tables: dict[str, list[dict]]) -> dict[str, int]:
    normalize_category_registry(tables)
    wiki_by_id = {row["person_id"]: row for row in tables["person_wiki"]}
    lives = {row["person_id"]: row for row in tables["person_section"] if row["section_key"] == "life"}
    stats: Counter[str] = Counter()

    for person in tables["person"]:
        person_id = person["id"]
        wiki = wiki_by_id.get(person_id, {})
        body = clean_wikipedia_bio(wiki.get("full_text", ""), stats)
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
            reasons.append("分类不在受控目录")
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
        if simplify_modern_text(body) != body:
            reasons.append("生平仍含繁体字")
        for line in body.splitlines():
            line = line.strip()
            if line and (REFERENCE_HEADING.match(line) or is_noise_line(line)):
                reasons.append("生平仍含参考或分类短行")
                break
            if line and (FAMILY_HEADING.match(line) or is_non_narrative_section_label(line)):
                reasons.append("生平仍含家族或作品等非叙事分栏")
                break
            if line and "".join(semantic_sentences(line)) != line:
                reasons.append("生平仍混入家族、作品或评价句")
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
