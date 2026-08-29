#!/usr/bin/env python3
"""Apply concise, original profile syntheses verified against Baidu Baike.

The mobile app intentionally keeps references out of the reading surface.  This
import stores the directly verified page URL in ``content_reference`` while the
reader sees only the two-state verification label.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import connect, initialize_database  # noqa: E402


PROFILES = {
    "zhangjuzheng": {
        "life": (
            "张居正（1525—1582），字叔大，号太岳，江陵人。早年由科举入仕，"
            "嘉靖二十六年（1547）中进士；此后历任吏部左侍郎兼东阁大学士等职，"
            "隆庆六年出任内阁首辅。万历初年，他主持政务十年，推动考成法、清丈田亩"
            "与赋役整饬，并参与北边与西南事务的决策。其去世后遭清算，至天启二年恢复名誉。"
            "著有《张太岳集》《书经直解》《帝鉴图说》等。"
        ),
        "family": "父亲：张文明。配偶：顾氏。子女：张敬修、张嗣修、张懋修、张简修、张允修。",
        "url": "https://baike.baidu.com/item/%E5%BC%A0%E5%B1%85%E6%AD%A3/279",
    },
    "zhuyuanzhang": {
        "life": (
            "朱元璋（1328—1398），字国瑞，濠州钟离人，明朝开国皇帝。少年家贫，"
            "曾入皇觉寺为僧，后参加红巾军；先后平定陈友谅、张士诚等割据势力，"
            "于1368年在应天即皇帝位。其统治时期推进卫所、里甲、黄册与鱼鳞图册等制度，"
            "调整中央和地方权力结构，并完成对西南、西北、辽东等地区的军事与行政整合。"
        ),
        "family": "配偶：马皇后等。子女包括朱标、朱樉、朱棡、朱棣、朱橚、朱桢、朱檀、朱椿、朱柏、朱桂、朱权等诸王，以及临安、宁国、安庆、怀庆等公主；完整亲属名录见人物关系页。",
        "url": "https://baike.baidu.com/item/%E6%9C%B1%E5%85%83%E7%92%8B/25626",
    },
}


def main() -> int:
    initialize_database()
    with connect() as db:
        for person_id, profile in PROFILES.items():
            db.execute(
                """
                UPDATE person
                SET biography = ?, family_summary = ?, verification_status = '已校验'
                WHERE id = ?
                """,
                (profile["life"], profile["family"], person_id),
            )
            db.executemany(
                """
                INSERT INTO person_section(person_id, section_key, title, position, content)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(person_id, section_key) DO UPDATE SET
                    title = excluded.title, position = excluded.position, content = excluded.content
                """,
                [
                    (person_id, "life", "生平（含教育背景）", 0, profile["life"]),
                    (person_id, "family", "家族与子嗣", 1, profile["family"]),
                ],
            )
            db.executemany(
                """
                INSERT INTO content_reference(content_type, content_id, section_key, position, title, url, locator, note)
                VALUES ('person', ?, ?, ?, '百度百科人物条目', ?, ?, '已核验人物身份与主要生平、家族信息')
                ON CONFLICT(content_type, content_id, section_key, position) DO UPDATE SET
                    title = excluded.title, url = excluded.url, locator = excluded.locator, note = excluded.note
                """,
                [
                    (person_id, "life", 2, profile["url"], person_id),
                    (person_id, "family", 1, profile["url"], person_id),
                ],
            )
    print(f"已导入 {len(PROFILES)} 份百度百科核验人物档案。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
