#!/usr/bin/env python3
"""以本地中文维基正文审计人物显示称号，并只修正可直接提取的职位或爵位。

人物页和朝代档案共用 ``person.title``。早期批量导入留下的“明朝官员”、
“明·某人”、谥号等泛称会误当作职位展示。本脚本只使用 ``person_wiki`` 的
传主导语与词条末尾分类标签，提取明确出现的官职、军职、爵位或文艺身份；
无法直接确认的记录会清空显示称号，绝不以分类名或猜测补写。

    backend/.venv/bin/python backend/scripts/audit_person_titles.py
    backend/.venv/bin/python backend/scripts/audit_person_titles.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"
REPORT = BACKEND.parent / "tmp" / "person-title-audit.json"

GENERIC_TITLE = re.compile(
    r"^(?:明(?:朝|代)?(?:官员|官員|將領|将领|人物|藩王|文人|勋臣|勳臣)|"
    r"宗室|文人|儒臣|武烈|荣定|榮定|僖武|介肃|介肅|忠毅|文靖|文贞|文端|"
    r"文忠|文毅|文节|文節|忠节|忠節|宪|憲)$"
)
HONORIFIC_TITLE = re.compile(r"^[一-龥]{1,4}(?:文|武|忠|烈|毅|靖|定|宣|庄|莊|简|簡|宪|憲|康|襄|恭|端|贞|貞|敏|节|節|壮|壯|义|義)$")
ROLE_ENDINGS = (
    "内阁首辅", "內閣首輔", "大学士", "大學士", "尚书", "尚書", "侍郎", "都御史", "总督", "總督",
    "巡抚", "巡撫", "督师", "督師", "都督同知", "都督佥事", "都督僉事", "都督", "指挥使", "指揮使", "总兵", "總兵", "副总兵", "副總兵",
    "参将", "參將", "游击", "游擊", "将军", "將軍", "元帅", "元帥", "布政使", "按察使", "知府", "知县",
    "御史", "给事中", "給事中", "祭酒", "学士", "學士", "太监", "太監", "皇后", "皇贵妃", "皇貴妃",
    "贵妃", "貴妃", "妃", "嫔", "嬪", "诗人", "詩人", "书法家", "書法家", "画家", "畫家", "文学家", "文學家", "医家", "醫家",
    "编修", "編修", "检讨", "檢討", "主事", "郎中", "通政使", "寺卿", "少保", "少傅", "少师", "少師",
    "太保", "太傅", "太师", "太師", "世子", "驸马", "駙馬", "国公", "國公", "教谕", "教諭",
    "作家", "詞人", "词人", "戏曲家", "戲曲家", "藏书家", "藏書家",
)
ROLE_TOKEN = re.compile(r"[一-龥]{1,14}(?:" + "|".join(sorted(map(re.escape, ROLE_ENDINGS), key=len, reverse=True)) + r")")
NOBLE_TOKEN = re.compile(r"[一-龥]{1,8}(?:王|公|侯|伯)")
GENERIC_CANDIDATE = re.compile(r"(?:明(?:朝|代)?(?:官员|官員|军事|軍事|将领|將領|人物)|开国功臣|開國功臣)$")
PLACEHOLDER_TITLE = re.compile(r"^明[·．.]|^明(?:朝|代)(?:官员|官員|將領|将领|人物|藩王|文人|勋臣|勳臣)$")
UNSAFE_CONTEXT = re.compile(r"(?:跟随|跟隨|随同|隨同|随|隨|從|随后|隨後|其后|其後|弹劾|彈劾|劾|荐|薦|遣|命|率|弟|父|子|岳父|自称|自稱|参考文献|參考文獻|由于|由於|母|妻|藩国|藩國|国王|國王|宗室|清朝|清代|清初|追赠|追贈|赠|贈)")


def load(name: str) -> list[dict]:
    path = CONTENT / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(name: str, rows: list[dict]) -> None:
    path = CONTENT / f"{name}.jsonl"
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def needs_review(person: dict) -> bool:
    title = (person.get("title") or "").strip()
    if not title:
        return False
    if PLACEHOLDER_TITLE.search(title) or GENERIC_TITLE.fullmatch(title) or HONORIFIC_TITLE.fullmatch(title):
        return True
    return False


def is_display_title(title: str) -> bool:
    """只让职位、爵位、内廷称号和文苑身份进入展示字段。"""

    if not title or PLACEHOLDER_TITLE.search(title) or GENERIC_TITLE.fullmatch(title) or HONORIFIC_TITLE.fullmatch(title):
        return False
    normalized = title.replace("兼", "、")
    parts = [part.strip() for part in re.split(r"[、，；;（）()]", normalized) if part.strip()]
    return bool(parts) and all(
        part.endswith(ROLE_ENDINGS) or (2 <= len(part) <= 10 and part.endswith(("王", "公", "侯", "伯")))
        for part in parts
    )


def clean_candidate(value: str) -> str:
    value = value.strip("，。；：、（）()「」『』《》 ")
    value = re.sub(
        r"^.*(?:追封为|追封為|追封|进封|進封|晋封|晉封|封为|封為|封|官至|累官|历官|歷官|历任|歷任|"
        r"授|拜为|拜為|拜|任|升任|升至|升|擢升|擢|迁任|遷任|迁|遷|进至|進至|至|为|為|以)",
        "",
        value,
    )
    for prefix in ("明朝", "明代", "中国", "中国明朝", "明初", "明末"):
        value = value.removeprefix(prefix)
    value = re.sub(r"^(?:元末明初|明末清初|晚明|万历年间|萬曆年間|崇祯时|崇禎時|嘉靖年间|嘉靖年間|官|改)", "", value)
    value = re.sub(r"^第[一二三四五六七八九十百千〇零]+子", "", value)
    return value.strip()


def is_safe_role(value: str) -> bool:
    if not value or len(value) > 16 or GENERIC_CANDIDATE.search(value):
        return False
    if UNSAFE_CONTEXT.search(value) or re.search(r"[，。；：]|(?:的|是|有|于|於)", value):
        return False
    return value.endswith(ROLE_ENDINGS)


def is_safe_noble(value: str) -> bool:
    return bool(
        2 <= len(value) <= 10
        and value.endswith(("王", "公", "侯", "伯"))
        and not GENERIC_CANDIDATE.search(value)
        and not UNSAFE_CONTEXT.search(value)
        and not re.search(r"(?:字|号|號|原名|又称|又稱|一字|今|现|現)", value)
    )


def candidate_score(value: str, position: int, noble: bool, category: str) -> tuple[int, int, int]:
    """优先官职、爵位，其次文艺身份；同类取靠近导语的表达。"""

    high = any(key in value for key in ("首辅", "首輔", "大学士", "大學士", "尚书", "尚書", "都御史", "总督", "總督", "巡抚", "巡撫", "督师", "督師"))
    noble = value.endswith(("王", "公", "侯", "伯"))
    military = any(key in value for key in ("都督", "指挥使", "指揮使", "总兵", "總兵", "将军", "將軍", "元帅", "元帥"))
    if category == "将帅":
        score = 5 if noble else 4 if military else 1
    elif category in {"宗藩", "帝王"}:
        score = 5 if noble else 2
    else:
        score = 5 if high else 3 if noble else 2 if military else 1
    return score, -position, -len(value)


def source_windows(wiki_text: str) -> list[tuple[str, int]]:
    """返回传主导语与词条末尾分类标签，避免从叙事中误取他人的职位。"""

    lines = [line.strip() for line in (wiki_text or "").splitlines() if line.strip()]
    if not lines:
        return []
    # 首句是词条对传主的身份概述；不从后续生平叙事取职，避免把亲属或对手的职位误给传主。
    windows = [(re.split(r"[。！!]", lines[0], maxsplit=1)[0], 2)]
    marker = next((index for index, line in enumerate(lines) if line in {"参考资料", "參考資料", "外部链接", "外部連結"}), None)
    if marker is not None:
        for line in lines[marker + 1:]:
            # 只采纳以时代/国别起首的分类标签；导航框里提到的亲属或他人会被排除。
            if (
                len(line) <= 28
                and not re.search(r"[。；：]", line)
                and re.match(r"^(?:明(?:朝|代)|中国|中國)", line)
            ):
                windows.append((line, 1))
    return windows


def title_from_wiki(person: dict, wiki_text: str) -> str:
    """只返回导语或分类标签中直接出现的单一职位/爵位；无证据时返回空。"""

    candidates: list[tuple[str, int, bool, int]] = []
    for text, source_rank in source_windows(wiki_text):
        for match in ROLE_TOKEN.finditer(text):
            value = clean_candidate(match.group())
            relation_context = text[max(0, match.start() - 8):match.start()]
            court_role = value.endswith(("皇后", "皇贵妃", "皇貴妃", "贵妃", "貴妃", "妃", "嫔", "嬪", "太监", "太監"))
            if (
                person.get("category") not in {"宗藩", "帝王"}
                and (person.get("category") == "内廷" or not court_role)
                and not re.search(r"(?:女|母|妻|父|子|弟|兄|祖|孙|孫)$", relation_context)
                and is_safe_role(value)
            ):
                candidates.append((value, match.start(), False, source_rank))
        for match in NOBLE_TOKEN.finditer(text):
            value = clean_candidate(match.group())
            context = text[max(0, match.start() - 16):match.end()]
            own_rank = source_rank == 1 or bool(re.search(r"封|爵|袭|襲", context))
            name_fragment = person.get("name", "").startswith(match.group()) or match.group().startswith(person.get("name", ""))
            if not name_fragment and is_safe_noble(value) and (person.get("category") in {"宗藩", "帝王"} or own_rank):
                candidates.append((value, match.start(), True, source_rank))
    if not candidates:
        return ""
    return max(
        candidates,
        key=lambda item: (item[3],) + candidate_score(item[0], item[1], item[2], person.get("category", "")),
    )[0]


def audit(apply: bool) -> dict:
    people = load("person")
    wiki_by_id = {row["person_id"]: row.get("full_text", "") for row in load("person_wiki")}
    changed: list[dict] = []
    cleared: list[dict] = []
    for person in people:
        if not needs_review(person):
            continue
        proposed = title_from_wiki(person, wiki_by_id.get(person["id"], ""))
        record = {"id": person["id"], "name": person["name"], "old_title": person.get("title", ""), "proposed_title": proposed}
        if proposed and proposed != person.get("title", ""):
            changed.append(record)
            if apply:
                person["title"] = proposed
        else:
            cleared.append(record)
            if apply:
                person["title"] = ""
    if apply:
        dump("person", people)
    report = {"reviewed": len(changed) + len(cleared), "changed": changed, "cleared": cleared}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = audit(args.apply)
    print(f"reviewed={report['reviewed']} directly_fixed={len(report['changed'])} cleared={len(report['cleared'])}")
    print(f"report={REPORT}")


if __name__ == "__main__":
    main()
