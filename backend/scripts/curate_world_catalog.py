#!/usr/bin/env python3
"""收束天下页内容：机构保留办事主体，典章只保留制度、器物与地点。

运行后直接更新 data/content 的 JSONL 真相；随后执行 content_store.py import 重建 SQLite。
"""

from __future__ import annotations

import json
from pathlib import Path


CONTENT = Path(__file__).resolve().parent.parent / "data" / "content"

# 这些是人工编写、可直接作为“典章”阅读的条目。其余 wiki-* 自动导入条目包含
# 同名机构、消歧义、影视与名单，不能继续和正式内容并列发布。
CURATED_SPECIAL_IDS = {
    "beijing-gugong",
    "nanjing-gugong",
    "ming-xiaoling",
    "shangfang-baojian",
    "wangming-qipai",
    "danshu-tiequan",
    "daming-baochao",
    "tingzhang-zhaoyu",
}

INSTITUTION_ADDITIONS = [
    {
        "id": "imperial-academy",
        "name": "国子监",
        "category": "教育礼制",
        "active_reigns": "洪武至崇祯",
        "function": "明代最高官学，隶属礼部，掌监生教育与部分学校政务；科举考试、学校教育与官僚养成在此相互衔接。",
        "source_id": "mingshi-editorial-v1",
    },
    {
        "id": "hanlin-academy",
        "name": "翰林院",
        "category": "中央政务",
        "active_reigns": "洪武至崇祯",
        "function": "掌修书撰史、起草诏制、经筵侍读与科举考校，是明代文官进入中枢的重要机构；不与内阁混同。",
        "source_id": "mingshi-editorial-v1",
    },
    {
        "id": "astronomical-bureau",
        "name": "钦天监",
        "category": "教育礼制",
        "active_reigns": "洪武至崇祯",
        "function": "掌天文观测、历法推算、授时与相关仪器事务。历法与礼制相连，其职掌不等同于后世单纯的气象机构。",
        "source_id": "mingshi-editorial-v1",
    },
    {
        "id": "imperial-medical-office",
        "name": "太医院",
        "category": "教育礼制",
        "active_reigns": "洪武至崇祯",
        "function": "掌宫廷诊疗、药材与医官事务，并承担部分医学生考核；其服务对象与地方医疗体系并不相同。",
        "source_id": "mingshi-editorial-v1",
    },
]

PROMOTIONS = {
    "imperial-academy": ["监生", "助教", "博士", "司业", "祭酒"],
    "hanlin-academy": ["庶吉士", "编修", "侍读／侍讲", "学士"],
    "astronomical-bureau": ["天文生", "博士", "监副", "监正"],
    "imperial-medical-office": ["医士", "御医", "院判", "院使"],
}


def read_rows(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(table: str, rows: list[dict], order: tuple[str, ...]) -> None:
    rows.sort(key=lambda row: tuple(row.get(key, 0) for key in order))
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    (CONTENT / f"{table}.jsonl").write_text(payload, encoding="utf-8")


def main() -> None:
    specials = [row for row in read_rows("special_item") if row["id"] in CURATED_SPECIAL_IDS]
    write_rows("special_item", specials, ("position", "id"))

    institutions = [row for row in read_rows("institution") if row["id"] not in {item["id"] for item in INSTITUTION_ADDITIONS}]
    institutions.extend(INSTITUTION_ADDITIONS)
    write_rows("institution", institutions, ("category", "id"))

    promotions = [row for row in read_rows("institution_promotion") if row["institution_id"] not in PROMOTIONS]
    promotions.extend(
        {"institution_id": institution_id, "position": position, "label": label}
        for institution_id, labels in PROMOTIONS.items()
        for position, label in enumerate(labels)
    )
    write_rows("institution_promotion", promotions, ("institution_id", "position"))

    # 新增机构暂不以“制度变革”凑条目；无可靠单项沿革则留空，比猜测年份更准确。
    reforms = [row for row in read_rows("institution_reform") if row["institution_id"] not in PROMOTIONS]
    write_rows("institution_reform", reforms, ("institution_id", "position"))
    print(f"机构 {len(institutions)} 条，典章 {len(specials)} 条")


if __name__ == "__main__":
    main()
