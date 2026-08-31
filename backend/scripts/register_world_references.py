#!/usr/bin/env python3
"""Register reader-facing reading and image-attribution metadata for 天下 content.

The JSONL content store remains authoritative.  This script is idempotent and deliberately
does not create institution/event or special/event association tables.
"""

from __future__ import annotations

import json
from pathlib import Path


CONTENT = Path(__file__).resolve().parents[1] / "data" / "content"
MINGSHI_URL = "https://zh.wikisource.org/wiki/明史"
IMAGE_NOTE = "应用内专题插绘，非外部文物图片或建筑实拍；仅作类别导览。许可：可随本应用发布。"

INSTITUTION_READINGS = {
    "中枢政务": ("《明史》职官志（卷72—76）", "职官志中的中枢政务及皇族事务条目"),
    "监察司法": ("《明史》职官志、刑法志（卷72—76、93—95）", "监察、审判与法制条目"),
    "军事卫所": ("《明史》兵志、职官志（卷72—76、89—92）", "卫所、军营与武官条目"),
    "内廷宦官": ("《明史》职官志（卷72—76）", "宫廷内官及相关职掌条目"),
    "地方治理": ("《明史》职官志、地理志（卷40—46、72—76）", "地方建置与官署条目"),
    "教育与专门": ("《明史》职官志、选举志（卷69—76）", "学校、科举与专门官署条目"),
}

SPECIAL_READINGS = {
    "beijing-gugong": ("《明史》地理志、礼志（卷40—58）", "京城、宫室与朝廷礼制条目"),
    "nanjing-gugong": ("《明史》地理志、礼志（卷40—58）", "南京建置、宫室与礼制条目"),
    "shangfang-baojian": ("《明史》仪卫志、兵志（卷64、89—92）", "皇帝仪卫、军器与赏赐相关条目"),
    "wangming-qipai": ("《明史》仪卫志（卷64）", "王命、仪卫与旗牌相关条目"),
    "danshu-tiequan": ("《明史》太祖本纪、功臣世表（卷1—3、105—107）", "开国功臣封赏与铁券相关条目"),
    "tingzhang-zhaoyu": ("《明史》刑法志（卷93—95）", "非常审讯、刑罚与司法程序条目"),
    "daming-baochao": ("《明史》食货志（卷77—82）", "宝钞、钱法与财政条目"),
    "ming-xiaoling": ("《明史》地理志、礼志（卷40—58）", "陵寝、京城与祭祀条目"),
    "imperial-examination": ("《明史》选举志（卷69—71）", "学校、科举与取士条目"),
    "yellow-register-fish-scale": ("《明史》食货志（卷77—82）", "户籍、田赋与赋役册籍条目"),
    "lijia-system": ("《明史》食货志（卷77—82）", "里甲、赋役与基层编制条目"),
    "single-whip-law": ("《明史》食货志（卷77—82）", "赋役折银与一条鞭法条目"),
    "great-ming-code": ("《明史》刑法志（卷93—95）", "律例、刑名与司法程序条目"),
    "weisuo-system": ("《明史》兵志、职官志（卷72—76、89—92）", "卫所、军籍与武官条目"),
    "maritime-prohibition-tribute": ("《明史》食货志、列传（卷77—82）", "海禁、互市与朝贡相关条目"),
    "yongle-encyclopedia": ("《明史》成祖本纪、艺文志（卷5—7、96—99）", "《永乐大典》修纂与明代著述条目"),
    "great-ming-statutes": ("《明史》礼志、职官志（卷47—58、72—76）", "会典、礼制与官制条目"),
    "ming-firearms": ("《明史》兵志（卷89—92）", "军器、火器与军制条目"),
    "ming-tombs": ("《明史》地理志、礼志（卷40—58）", "帝陵、京畿与祭祀条目"),
    "temple-of-heaven": ("《明史》礼志、地理志（卷40—58）", "郊祀、坛庙与京城条目"),
    "imperial-ancestral-temple": ("《明史》礼志（卷47—58）", "宗庙、祭祀与礼制条目"),
    "wudang-palace-complex": ("《明史》地理志、成祖本纪（卷5—7、40—46）", "湖北建置与永乐营建相关条目"),
}


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(name: str, rows: list[dict]) -> None:
    rows.sort(key=lambda row: (row["content_type"], row["content_id"], row["section_key"], row["position"]))
    (CONTENT / name).write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    references = load("content_reference.jsonl")
    institutions = load("institution.jsonl")
    specials = load("special_item.jsonl")
    references = [
        row for row in references
        if not (
            row["content_type"] in {"institution", "special"}
            and row["section_key"] in {"reading", "image"}
        )
    ]
    next_id = max(row["id"] for row in references) + 1

    for institution in institutions:
        title, locator = INSTITUTION_READINGS[institution["category"]]
        references.append({
            "id": next_id,
            "content_type": "institution",
            "content_id": institution["id"],
            "section_key": "reading",
            "position": 0,
            "title": title,
            "url": MINGSHI_URL,
            "locator": locator,
            "note": "用于机构职掌、属官与设置沿革的延伸阅读。",
        })
        next_id += 1

    for special in specials:
        title, locator = SPECIAL_READINGS[special["id"]]
        references.append({
            "id": next_id,
            "content_type": "special",
            "content_id": special["id"],
            "section_key": "reading",
            "position": 0,
            "title": title,
            "url": MINGSHI_URL,
            "locator": locator,
            "note": "用于条目正文的延伸阅读。",
        })
        next_id += 1
        references.append({
            "id": next_id,
            "content_type": "special",
            "content_id": special["id"],
            "section_key": "image",
            "position": 0,
            "title": "应用内专题插绘",
            "url": "",
            "locator": "非文物实拍",
            "note": IMAGE_NOTE,
        })
        next_id += 1

    dump("content_reference.jsonl", references)
    print(f"已登记：机构延伸阅读 {len(institutions)} 条；典章延伸阅读与图片许可 {len(specials) * 2} 条。")


if __name__ == "__main__":
    main()
