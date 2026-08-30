#!/usr/bin/env python3
"""深度补全：家族与子嗣名录、亲属关系网络、维基全文生平。

用法：
  python scripts/enrich_profiles_deep.py --phase family   # 家族名录（百度百科名片+维基数据声明）
  python scripts/enrich_profiles_deep.py --phase relations # 亲属关系网络（同一名片来源）
  python scripts/enrich_profiles_deep.py --phase life-wiki # 维基百科全文加深生平（网络窗口期）

规则：
- 56 位核心人物的人工校订“家族与子嗣”“生平”栏目一律不覆盖。
- 关系只建双侧都在库内的家庭类边（父子/母子/配偶/兄弟姐妹）；皇帝的宗室
  家庭关系允许，臣属关系仍不建。
- 维基全文写库前须通过标题一致与生卒年校验；网络不可达时整阶段跳过。
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import connect, initialize_database  # noqa: E402
from enrich_people_from_baike import fetch_json, BAIKE_API  # noqa: E402
from enrich_people_from_wikidata import entity_data, entity_ids, label  # noqa: E402
from enrich_people_from_wikipedia import (  # noqa: E402
    WIKI_API,
    api as wiki_api,
    search_zh_article,
    zh_wikipedia_reachable,
)

TAG_PATTERN = re.compile(r"<[^>]+>")
THIN_LIFE = 450
KINSHIP_FIELDS = {"父亲": "父", "母亲": "母", "配偶": "配", "皇后": "配", "妻子": "配", "儿子": "子", "女儿": "女", "兄弟姐妹": "手足", "兄弟": "手足", "姐妹": "手足"}
WD_KINSHIP = (("P22", "父"), ("P25", "母"), ("P26", "配"), ("P40", "子"), ("P3373", "手足"))
ROSTER_TITLES = {"父": "父亲", "母": "母亲", "配": "配偶", "子": "子女", "女": "女儿", "手足": "兄弟姐妹"}


def clean(value: str) -> str:
    return TAG_PATTERN.sub("", value).replace("\u00a0", " ").strip()


def base_name(value: str) -> str:
    return value.split("（")[0].split("(")[0].strip()


def baike_lemma(name: str) -> dict:
    try:
        return fetch_json(f"{BAIKE_API}?scope=103&format=json&appid=379020&bk_length=800&bk_key={quote(name)}")
    except Exception:
        return {}


def kinship_groups(lemma: dict) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {role: [] for role in ("父", "母", "配", "子", "女", "手足")}
    for item in lemma.get("card", []):
        field = clean(item.get("name", ""))
        role = KINSHIP_FIELDS.get(field)
        if not role:
            continue
        for value in item.get("value", []):
            name = base_name(clean(value))
            if name and name not in groups[role]:
                groups[role].append(name)
    return groups


def parse_years(text: str) -> tuple[int | None, int | None]:
    match = re.match(r"^\s*([?？\d]{1,4})\s*—\s*([?？\d]{1,4})\s*$", text or "")
    if match:
        return (
            int(match.group(1)) if match.group(1).isdigit() else None,
            int(match.group(2)) if match.group(2).isdigit() else None,
        )
    years = re.findall(r"(1[3-7]\d{2})", text)
    return (int(years[0]) if years else None, int(years[1]) if len(years) > 1 else None)


def wiki_identity_ok(person, title: str, extract_head: str) -> bool:
    if title != person["name"]:
        if not (title.endswith(person["name"]) and len(title) - len(person["name"]) <= 4):
            return False
    expected_birth, expected_death = parse_years(person["years"])
    actual_birth, actual_death = parse_years(extract_head[:120])
    if expected_birth and actual_birth and abs(expected_birth - actual_birth) > 6:
        return False
    if expected_death and actual_death and abs(expected_death - actual_death) > 6:
        return False
    return True


FAMILY_HINTS = (
    "父亲", "母亲", "之妻", "妻子", "配偶", "继室", "原配", "皇后", "妃", "长子", "次子",
    "生子", "有子", "其子", "诸子", "之子", "兄弟", "长女", "次女", "女儿",
    "之孙", "其孙", "胞弟", "其兄", "其弟", "兄长", "娶", "育有",
)


def family_sentences(abstract: str, limit: int = 4) -> list[str]:
    """从词条摘要中挑出含亲属信息的句子，供无名片亲属字段的人物使用。"""

    sentences = [s.strip() for s in re.split(r"(?<=[。！？])", abstract or "") if s.strip()]
    picked = [s for s in sentences if any(hint in s for hint in FAMILY_HINTS)]
    # 摘要里的人物自身称谓（如“其子朱标”）比泛匹配可靠；过滤明显跑题的短句。
    return [s for s in picked if len(s) >= 12][:limit]


def load_state():
    with connect() as db:
        people = db.execute("SELECT id, name, years, category, reign FROM person ORDER BY id").fetchall()
        curated_family = {
            row["person_id"]
            for row in db.execute("SELECT person_id FROM person_section WHERE section_key = 'family' AND length(trim(content)) > 0")
        }
        source_id = db.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
        existing_pairs = {
            (r[0], r[1], r[2])
            for r in db.execute("SELECT from_person_id, to_person_id, relation_type FROM person_relation")
        }
        wd_matched = {
            row["person_id"]: row["entity_id"]
            for row in db.execute(
                "SELECT person_id, entity_id FROM person_research WHERE provider IN ('wikidata','wikipedia') AND status='matched' AND entity_id <> ''"
            )
        }
        life_length = {
            row["person_id"]: len(row["content"])
            for row in db.execute("SELECT person_id, content FROM person_section WHERE section_key = 'life'")
        }
    return people, curated_family, source_id, existing_pairs, wd_matched, life_length


def tolerant_entity_data(ids) -> dict:
    """维基数据批量拉取的容错包装：整体看门狗 90 秒，失败只降级跳过。"""

    ids = sorted(set(ids))
    if not ids:
        return {}
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(entity_data, ids)
        try:
            return future.result(timeout=90)
        except FuturesTimeoutError:
            print("维基数据批量拉取超过 90 秒，跳过实体标签补全。", flush=True)
            return {}
        except Exception as error:
            print(f"维基数据批量拉取失败（{error}），跳过实体标签补全。", flush=True)
            return {}


def run_family_and_relations(people, curated_family, source_id, existing_pairs, wd_matched, sleep: float) -> None:
    """单遍百度百科抓取：同时产出家族名录栏目与库内亲属关系边。"""

    entity_map = tolerant_entity_data(set(wd_matched.values()))
    entity_to_person = {entity_id: pid for pid, entity_id in wd_matched.items()}
    # 亲属声明里引用的是“亲属的实体 id”，只有当亲属本身也是已匹配的库内人物时才能建边。
    lookup_cache: dict[str, dict] = {}

    def wd_labels(entity: dict) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        related = {value for _, role in WD_KINSHIP for value in entity_ids(entity, property_for(role))}
        missing = [rid for rid in related if rid not in lookup_cache]
        if missing:
            lookup_cache.update(tolerant_entity_data(missing))
        for property_id, role in WD_KINSHIP:
            names = [label(lookup_cache.get(value, {})) for value in entity_ids(entity, property_id)]
            names = [name for name in names if name]
            if names:
                groups[role] = names
        return groups

    # 维基数据标签补齐
    wd_group_cache: dict[str, dict[str, list[str]]] = {}
    for person_id, entity_id in wd_matched.items():
        entity = entity_map.get(entity_id)
        if entity:
            wd_group_cache[person_id] = wd_labels(entity)

    name_to_ids: dict[str, list[str]] = {}
    for person in people:
        name_to_ids.setdefault(person["name"], []).append(person["id"])

    planned: dict[tuple[str, str, str], str] = {}

    def plan(from_id: str, to_id: str, relation_type: str) -> None:
        if from_id == to_id:
            return
        if relation_type in ("配偶", "兄弟姐妹") and from_id > to_id:
            from_id, to_id = to_id, from_id
        key = (from_id, to_id, relation_type)
        if key in planned or key in existing_pairs:
            return
        planned[key] = "明代"

    family_written = 0
    with connect() as db:
        for person in people:
            person_id = person["id"]
            lemma = baike_lemma(person["name"])
            groups = kinship_groups(lemma)
            if person_id in wd_group_cache:
                for role, names in wd_group_cache[person_id].items():
                    for name in names:
                        if name not in groups[role]:
                            groups[role].append(name)

            # 1) 家族名录栏目（人工校订的 56 位不动）
            if person_id not in curated_family:
                lines = [f"{ROSTER_TITLES[role]}：{'、'.join(names)}。" for role, names in groups.items() if names]
                if not lines:
                    # 名片无亲属字段时退回摘要亲属句。
                    lines = family_sentences(lemma.get("abstract", ""))
                if lines:
                    lines.append("以上为公开资料所载亲属信息；各成员结局仍待逐条编核。")
                    content = "\n".join(lines)
                    db.execute(
                        """
                        INSERT INTO person_section(person_id, section_key, title, position, content)
                        VALUES (?, 'family', '家族', 1, ?)
                        ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content
                        """,
                        (person_id, content),
                    )
                    db.execute("UPDATE person SET family_summary = ? WHERE id = ?", (content, person_id))
                    family_written += 1

            # 2) 亲属关系边：仅当亲属名能在库内唯一命中
            def resolve(name: str) -> str | None:
                ids = name_to_ids.get(name, [])
                return ids[0] if len(ids) == 1 else None

            for name in groups["父"]:
                target = resolve(name)
                if target:
                    plan(target, person_id, "父子")
            for name in groups["母"]:
                target = resolve(name)
                if target:
                    plan(target, person_id, "母子")
            for name in groups["配"]:
                target = resolve(name)
                if target:
                    plan(person_id, target, "配偶")
            for name in groups["子"] + groups["女"]:
                target = resolve(name)
                if target:
                    plan(person_id, target, "父子")
            for name in groups["手足"]:
                target = resolve(name)
                if target:
                    plan(person_id, target, "兄弟姐妹")
            time.sleep(sleep)

        # 年号归属：父子/母子取子方年号，配偶/手足取 id 较小一方的年号
        reign_by_id = {p["id"]: p["reign"] or "明代" for p in people}
        rows = []
        for (from_id, to_id, relation_type), _ in planned.items():
            reign = reign_by_id.get(to_id, "明代") if relation_type in ("父子", "母子") else reign_by_id.get(from_id, "明代")
            rows.append((from_id, to_id, relation_type, reign, "", source_id))
        db.executemany(
            """
            INSERT OR IGNORE INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        total = db.execute("SELECT COUNT(*) FROM person_relation").fetchone()[0]
    print(f"[family+relations] 家族名录写库 {family_written} 位；新增关系 {len(rows)} 条，全库现 {total} 条。", flush=True)


def run_cowork_relations(people, existing_pairs, source_id) -> None:
    """事件共现网络：同一事件的参与者（帝王除外）两两建“同僚”关系边。"""

    with connect() as db:
        events = db.execute(
            """
            SELECT e.id, e.year, e.title, e.participants, r.title AS reign_title
            FROM event e JOIN reign r ON r.id = e.reign_id
            """
        ).fetchall()
        category_by_name = {row["name"]: row["category"] for row in db.execute("SELECT name, category FROM person")}
        name_to_ids: dict[str, list[str]] = {}
        for person in people:
            name_to_ids.setdefault(person["name"], []).append(person["id"])
        reign_by_id = {p["id"]: p["reign"] or "明代" for p in people}

        rows = []
        for event in events:
            ids = []
            for name in [n for n in (event["participants"] or "").split("、") if n]:
                person_ids = name_to_ids.get(name, [])
                if len(person_ids) == 1 and category_by_name.get(name) != "帝王":
                    ids.append(person_ids[0])
            ids = sorted(set(ids))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    key = (ids[i], ids[j], "同僚")
                    if key in existing_pairs:
                        continue
                    existing_pairs.add(key)
                    reign = reign_by_id.get(ids[i], event["reign_title"])
                    note = f"共事于{event['year'] or ''}年{event['title']}".replace("年年", "年")
                    rows.append((*key, reign, note, source_id))
        db.executemany(
            """
            INSERT OR IGNORE INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        total = db.execute("SELECT COUNT(*) FROM person_relation").fetchone()[0]
    print(f"[cowork] 事件共现新增关系 {len(rows)} 条，全库现 {total} 条。", flush=True)


def property_for(role: str) -> str:
    return {"父": "P22", "母": "P25", "配": "P26", "子": "P40", "手足": "P3373"}[role]


def run_life_wiki(people, life_length, sleep: float) -> None:
    """维基百科全文加深生平：网络不可达时整阶段跳过。"""

    if not zh_wikipedia_reachable():
        print("[life-wiki] 中文维基百科不可达，本阶段跳过；网络窗口期重跑即可。", flush=True)
        return
    targets = [p for p in people if life_length.get(p["id"], 0) < THIN_LIFE]
    print(f"[life-wiki] 生平偏薄待加深 {len(targets)} 位。", flush=True)
    written = 0
    for index, person in enumerate(targets, start=1):
        try:
            title = search_zh_article(person["name"])
            extract = wiki_full_extract(title) if title else None
        except Exception as error:
            print(f"[life-wiki] {person['name']}: 抓取失败（{error}）", flush=True)
            time.sleep(sleep)
            continue
        if not extract:
            time.sleep(sleep)
            continue
        if not wiki_identity_ok(person, title, extract):
            time.sleep(sleep)
            continue
        trimmed = extract[:5000]
        if len(extract) > 5000:
            trimmed = extract[:5000].rsplit("。", 1)[0] + "。"
        with connect() as db:
            db.execute(
                """
                INSERT INTO person_section(person_id, section_key, title, position, content)
                VALUES (?, 'life', '生平', 0, ?)
                ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content
                """,
                (person["id"], trimmed),
            )
            db.execute("UPDATE person SET verification_status = '已校验' WHERE id = ?", (person["id"],))
        written += 1
        if index % 50 == 0:
            print(f"[life-wiki] 已处理 {index}/{len(targets)}，写库 {written}。", flush=True)
        time.sleep(sleep)
    print(f"[life-wiki] 全文生平写库 {written} 位。", flush=True)


def wiki_full_extract(title: str) -> str | None:
    result = wiki_api(
        WIKI_API,
        {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": "1",
            "redirects": "1",
            "format": "json",
            "formatversion": "2",
        },
    )
    for page in result.get("query", {}).get("pages", []):
        if "missing" not in page:
            return (page.get("extract") or "").strip() or None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="深度补全家formed族名录、关系网络与维基全文生平")
    parser.add_argument("--phase", choices=["family", "relations", "cowork", "life-wiki", "all"], default="all")
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=0, help="限制处理条数，0 表示不限制")
    parser.add_argument("--skip-wikidata", action="store_true", help="跳过维基数据标签补全，只用百度百科")
    args = parser.parse_args()

    initialize_database()
    people, curated_family, source_id, existing_pairs, wd_matched, life_length = load_state()
    if args.skip_wikidata:
        wd_matched = {}
    if args.limit:
        people = people[: args.limit]
    print(f"待处理人物 {len(people)} 位；已有人工校订家族栏目 {len(curated_family)} 位。", flush=True)
    if args.phase in ("family", "relations", "all"):
        run_family_and_relations(people, curated_family, source_id, existing_pairs, wd_matched, args.sleep)
    if args.phase in ("cowork", "all"):
        run_cowork_relations(people, existing_pairs, source_id)
    if args.phase in ("life-wiki", "all"):
        run_life_wiki(people, life_length, args.sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
