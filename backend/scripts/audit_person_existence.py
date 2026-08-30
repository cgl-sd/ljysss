#!/usr/bin/env python3
"""审计发布人物是否有可匹配的明朝中文维基百科介绍，不改写内容库。

人物页的保留门槛只有一条：中文维基百科的正文必须能识别为当前人物，且简介须明确
属于明朝（含南明）。《明史》卷次、CBDB 记录或百度百科链接只能用于编辑核对，不能
替代维基百科人物介绍；因此，同名但正文是他朝人物的记录必须删除。脚本输出：

* ``confirmed``：维基简介匹配当前人物，且含明代信号；
* ``rejected``：不是人物实体、没有可比对的维基正文、命中同名他朝人物，或无法确认
  为明朝人物。

维基正文优先取 ``person_wiki``；只有 URL 而没有缓存正文的条目，会只读扫描本地
``sources/wikipedia_zh`` parquet 包补齐审计证据。结果写到 gitignore 的 ``tmp/``，
不改变 ``data/content/*.jsonl``。

    backend/.venv/bin/python backend/scripts/audit_person_existence.py
    backend/.venv/bin/python backend/scripts/audit_person_existence.py --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

from opencc import OpenCC


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
CONTENT = BACKEND / "data" / "content"
STAGING = BACKEND / "data" / "staging"
MINGSHI_CORPUS = BACKEND / "sources" / "mingshi_full"
WIKIPEDIA_PACKS = [BACKEND / "sources" / "wikipedia_zh" / f"train-0000{i}.parquet" for i in range(6)]
DEFAULT_REPORT = ROOT / "tmp" / "person-existence-audit.json"

t2s = OpenCC("t2s")

ERAS = (
    "洪武", "建文", "永乐", "洪熙", "宣德", "正统", "景泰", "天顺", "成化", "弘治",
    "正德", "嘉靖", "隆庆", "万历", "泰昌", "天启", "崇祯", "弘光", "隆武", "绍武", "永历",
)
MING_MARK = re.compile(r"明朝|明代|明初|明末|明中叶|元末明初|南明|明太祖|明成祖|朱元璋")
OTHER_DYNASTY = re.compile(
    r"(西周|东周|春秋|战国|秦末|秦朝|西汉|东汉|汉朝|晋朝|南北朝|北魏|隋朝|唐朝|唐代|"
    r"五代|辽朝|金朝|南宋|北宋|宋代|宋朝|元代|元朝|三国|清朝|清代|民国)"
    r"[^\n，。]{0,14}?(?:将领|名将|名臣|大臣|皇帝|政治家|学者|官员|人物|宗室|宰相|进士|诗人|外戚|画家|书法家)"
)
DISAMBIGUATION_HEAD = re.compile(
    r"(?:可指|可以指|可能是指|下列.*?名字为|下列.*?人物|数个名为|可指下列人物|"
    r"下列公主有封号)"
)
CALENDAR_LABEL = re.compile(r"^[元一二三四五六七八九十百千〇○零]+年$")
GENERIC_TITLES = {"明代官员", "明代人物", "明朝人物", "宗室", "后妃", "宦官", "文人", "功臣"}

# 少数维基以谥号、帝号或单名立条。这里是经正文、家世或官历逐一核定过的等价标题，
# 不把「明朝」一类泛称当作人物别名。新增别名时必须同时核对条目正文。
WIKIPEDIA_IDENTITY_TITLES = {
    "zhuyuyu": {"绍武帝"},
    "jishufei": {"孝穆纪太后"},
    "qishijiao": {"亓诗教", "诗教"},
    "mahuanghou": {"孝慈高皇后 (明朝)"},
    "nankanggongzhu": {"朱玉华"},
    "zhuyoubin": {"朱祐檳"},
    "zhuyouhui": {"朱祐楎"},
}


def load(table: str, directory: Path = CONTENT) -> list[dict]:
    path = directory / f"{table}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def simplify(value: str) -> str:
    return t2s.convert(value or "").strip()


def wiki_title_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc != "zh.wikipedia.org" or not parsed.path.startswith("/wiki/"):
        return ""
    return simplify(unquote(parsed.path.removeprefix("/wiki/")).replace("_", " "))


def base_wiki_title(title: str) -> str:
    """去掉维基为消歧添加的括号说明，保留可以与姓名比对的主标题。"""

    return re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", simplify(title)).strip()


def is_calendar_label(name: str) -> bool:
    """年月、卷次等不能成为人物，即使碰巧有同名百科页。"""

    return bool(CALENDAR_LABEL.fullmatch(simplify(name)))


def aliases(person: dict) -> set[str]:
    """仅从已展示的姓名和称号中取别名，不凭猜测扩展同名。"""

    values = {simplify(person.get("name", ""))}
    for item in re.split(r"[·、/／]", simplify(person.get("title", ""))):
        item = item.strip("（）() ")
        if len(item) >= 3 and item not in GENERIC_TITLES:
            values.add(item)
    return values - {""}


def has_ming_signal(text: str) -> bool:
    text = simplify(text)
    return bool(MING_MARK.search(text) or any(era in text for era in ERAS))


def has_other_dynasty_signal(text: str) -> bool:
    return bool(OTHER_DYNASTY.search(simplify(text)))


def is_disambiguation_page(text: str) -> bool:
    """消歧页罗列多个同名者，不是可供人物库使用的单一人物介绍。"""

    # 标记必须出现在导语：正文中“无赃可指”之类普通叙述不能被误判为消歧页。
    head = "\n".join(line.strip() for line in simplify(text).splitlines() if line.strip())[:240]
    return bool(DISAMBIGUATION_HEAD.search(head))


def wiki_identity_evidence(person: dict, text: str, wiki_title: str = "") -> tuple[bool, bool, bool]:
    """返回（姓名或称号匹配、明代信号、他朝直接证伪）。"""

    full_text = simplify(text)
    head = full_text[:1200]
    title = simplify(wiki_title)
    identity = base_wiki_title(title) == simplify(person.get("name", "")) or any(
        alias in head for alias in aliases(person)
    ) or title in {
        simplify(value) for value in WIKIPEDIA_IDENTITY_TITLES.get(person.get("id", ""), set())
    }
    # 年代或类别说明有时在生平、分类行而不在首句，故可检索整篇条目；他朝身份则只认
    # 开头的自我介绍，避免把正文中提到的前朝史实误判为传主所属朝代。
    ming = has_ming_signal(full_text)
    other = has_other_dynasty_signal(head) and not ming
    return identity, ming, other


def roster_direct_evidence(name: str, openings: list[str]) -> bool:
    """确认《明史》名录中的对应卷次确以该姓名起传。

    卷次定位本身不够：同名误配和错误分段都会留下定位。要求传文开头就是姓名，
    同时由 ``is_calendar_label`` 在调用方拦截「九年」之类纪年伪标题。
    """

    name = simplify(name)
    return any(simplify(opening).startswith(f"{name}，") or simplify(opening).startswith(f"{name},")
               for opening in openings)


def classify(
    person: dict,
    wiki_text: str,
    mingshi_excerpts: list[str],
    roster_openings: list[str],
    corpus_juans: set[int],
    in_roster: bool,
    wiki_title: str = "",
) -> tuple[str, str]:
    """根据可复核的本地文本返回（结论、理由）。

    《明史》相关参数仅写入审计证据，不能越过中文维基百科的保留门槛。
    """

    name = simplify(person.get("name", ""))
    if is_calendar_label(name):
        return "rejected", "姓名是纪年词，不是人物实体"
    if is_disambiguation_page(wiki_text):
        return "rejected", "维基正文是消歧页，未指向单一人物介绍"

    identity, ming, other = wiki_identity_evidence(person, wiki_text, wiki_title)
    if other:
        return "rejected", "维基简介明确是其他朝代同名人物"
    if identity and ming:
        return "confirmed", "维基简介匹配本人且含明代信号"

    if not wiki_text:
        return "rejected", "没有可比对的中文维基百科正文"
    if not identity:
        return "rejected", "维基简介未匹配当前人物，可能是同名错配"
    if not ming:
        return "rejected", "维基简介缺少明确明代信号"
    return "rejected", "没有可复核的中文维基百科人物介绍"


def fetch_missing_wiki_text(wanted_titles: set[str]) -> dict[str, str]:
    """一次扫描离线维基包，为仅存 URL 的人物补审计文本；不写回内容库。"""

    if not wanted_titles:
        return {}
    try:
        import pyarrow.parquet as pq
    except ImportError as error:  # pragma: no cover - deployment safeguard
        raise SystemExit("缺少 pyarrow，无法读取本地 wikipedia_zh 包") from error

    hits: dict[str, str] = {}
    for pack in WIKIPEDIA_PACKS:
        if not pack.exists():
            raise SystemExit(f"缺少维基来源包：{pack}")
        reader = pq.ParquetFile(str(pack))
        for batch in reader.iter_batches(columns=["title", "text"], batch_size=4096):
            titles = batch.column("title").to_pylist()
            texts = batch.column("text").to_pylist()
            for title, text in zip(titles, texts):
                key = simplify(title)
                if key in wanted_titles and key not in hits:
                    hits[key] = text or ""
    return hits


def corpus_direct_mentions(names: set[str]) -> dict[str, set[int]]:
    """返回《明史》定形语料中以人物名直接起句的卷次。

    此证据用于确认人物存在，不代替详情栏目应有的段级出处。泛称「某氏」不以词面
    命中自动确认，避免把无法消歧的女性姓氏条目误当作唯一人物。
    """

    if not MINGSHI_CORPUS.exists():
        raise SystemExit(f"缺少《明史》语料：{MINGSHI_CORPUS}")
    found: dict[str, set[int]] = defaultdict(set)
    for path in sorted(MINGSHI_CORPUS.glob("卷*.txt")):
        match = re.search(r"卷(\d+)\.txt$", path.name)
        if not match:
            continue
        juan = int(match.group(1))
        for line in path.read_text(encoding="utf-8").splitlines():
            head = simplify(re.split(r"[，,]", line, maxsplit=1)[0])
            if head in names:
                found[head].add(juan)
    return found


def audit(fetch_missing: bool, include_profiles: bool = False):
    people = load("person")
    references = load("content_reference")
    wiki_rows = load("person_wiki")
    mingshi_rows = load("person_mingshi")

    wiki_by_person = {row["person_id"]: row.get("full_text", "") for row in wiki_rows}
    wiki_title_by_person = {row["person_id"]: row.get("wiki_title", "") for row in wiki_rows}
    mingshi_by_person: dict[str, list[str]] = defaultdict(list)
    for row in mingshi_rows:
        mingshi_by_person[row["person_id"]].append(row.get("excerpt", ""))
    wiki_url_by_person: dict[str, list[str]] = defaultdict(list)
    for row in references:
        if row.get("content_type") != "person":
            continue
        if row.get("url"):
            title = wiki_title_from_url(row["url"])
            if title:
                wiki_url_by_person[row["content_id"]].append(title)

    if fetch_missing:
        wanted = {
            title
            for person in people
            if not wiki_by_person.get(person["id"], "")
            for title in wiki_url_by_person.get(person["id"], [])
        }
        # 早期导入有少量条目只留下了《明史》或百度来源。对这类人用姓名精确查询离线
        # 中文维基包；命中仍须经过下方的同名与朝代检验，不能直接视为通过。
        wanted.update(
            simplify(person["name"])
            for person in people
            if not wiki_by_person.get(person["id"], "")
        )
        fetched = fetch_missing_wiki_text(wanted)
        for person in people:
            if wiki_by_person.get(person["id"], ""):
                continue
            for title in [*wiki_url_by_person.get(person["id"], []), simplify(person["name"])]:
                if text := fetched.get(title):
                    wiki_by_person[person["id"]] = text
                    wiki_title_by_person[person["id"]] = title
                    break

    rows: list[dict] = []
    for person in people:
        person_id = person["id"]
        wiki_text = wiki_by_person.get(person_id, "")
        wiki_title = wiki_title_by_person.get(person_id, "")
        name = simplify(person["name"])
        status, reason = classify(
            person,
            wiki_text,
            [],
            [],
            set(),
            False,
            wiki_title,
        )
        identity, ming, other = wiki_identity_evidence(person, wiki_text, wiki_title)
        rows.append({
            "id": person_id,
            "name": person["name"],
            "category": person["category"],
            "reign": person["reign"],
            "status": status,
            "reason": reason,
            "evidence": {
                "in_mingshi_roster": False,
                "mingshi_direct_roster_match": False,
                "mingshi_corpus_direct_juans": [],
                "mingshi_excerpt_count": len(mingshi_by_person.get(person_id, [])),
                "has_wikipedia_url": bool(wiki_url_by_person.get(person_id)),
                "has_wikipedia_text": bool(wiki_text),
                "wikipedia_title": wiki_title,
                "wiki_identity_match": identity,
                "wiki_ming_signal": ming,
                "wiki_other_dynasty_signal": other,
            },
        })

    counts = Counter(row["status"] for row in rows)
    summary = {
        "total": len(rows),
        "confirmed": counts["confirmed"],
        "review": counts["review"],
        "rejected": counts["rejected"],
        "confirmed_with_wrong_wiki_text": 0,
        "review_by_reason": dict(Counter(row["reason"] for row in rows if row["status"] == "review")),
        "rejected_people": [
            {key: row[key] for key in ("id", "name", "reason")} for row in rows if row["status"] == "rejected"
        ],
    }
    if include_profiles:
        return summary, rows, {
            person_id: {
                "wiki_title": wiki_title_by_person.get(person_id, ""),
                "full_text": text,
            }
            for person_id, text in wiki_by_person.items()
            if text
        }
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-fetch", action="store_true", help="不扫描离线维基包，只审计现有正文")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="JSON 审计报告路径")
    parser.add_argument("--strict", action="store_true", help="存在待核或排除项时以非零状态退出")
    args = parser.parse_args()

    summary, rows = audit(fetch_missing=not args.no_fetch)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"summary": summary, "people": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("人物存在性审计：" + "｜".join(f"{key} {summary[key]}" for key in ("total", "confirmed", "review", "rejected")))
    if summary["rejected_people"]:
        print("明确排除：" + "、".join(f"{row['name']}（{row['reason']}）" for row in summary["rejected_people"]))
    print(f"报告：{args.report}")
    if args.strict and (summary["review"] or summary["rejected"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
