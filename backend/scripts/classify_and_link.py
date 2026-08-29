#!/usr/bin/env python3
"""归类与关联收尾：

1. “其他”分类的人物按传文关键词归入六分类（内廷/封爵/将帅/文苑/朝臣），
   全库不再有“精选/全量”之分。
2. 为事件补参与人物：扫描事件正文出现的库内人物姓名（长名优先）。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

KEYWORDS = [
    ("内廷", r"宦官|太监|司礼监|御马监|内官|皇后|皇贵妃|贵妃|妃|太后|太皇太后|嫔|选侍|宫人|女官"),
    ("封爵", r"封[^，。]{0,4}(?:公|侯|伯)|袭爵|嗣(?:公|侯|伯)位|驸马|亲王|郡王|藩王|镇国将军|辅国将军|公主"),
    ("将帅", r"总兵|都督|指挥使|指挥同知|指挥佥事|参将|游击|副将军|左副将军|征虏|征南|征西|征南将军|卫指挥|都指挥|把总|守备|千户|百户|都司"),
    ("文苑", r"诗人|诗文|工诗|善诗|文学家|画家|书法家|戏曲|小说|藏书家|文人|古文|辞章|以文名|善画|能画|琴曲|隐居|出家|僧|道士|医家|名医"),
    ("朝臣", r"进士|尚书|侍郎|御史|巡抚|知府|知县|布政使|按察使|给事中|内阁|大学士|主事|郎中|总督|学士|入仕|为官"),
]


def main() -> int:
    app = sqlite3.connect(BACKEND / "data" / "ming_history.sqlite3")
    app.row_factory = sqlite3.Row

    # ---- 1) 归类“其他” ----
    moved = 0
    others = app.execute("SELECT id, name, biography FROM person WHERE category = '其他'").fetchall()
    for row in others:
        text = (row["biography"] or "")[:900]
        assigned = None
        for cat, pattern in KEYWORDS:
            if re.search(pattern, text):
                assigned = cat
                break
        if assigned is None:
            assigned = "朝臣"
        app.execute("UPDATE person SET category = ? WHERE id = ?", (assigned, row["id"]))
        moved += 1
    print(f"归类完成 {moved} 位。", flush=True)

    # ---- 2) 事件补参与人物 ----
    names = [(r["name"], len(r["name"])) for r in app.execute("SELECT name FROM person")]
    names.sort(key=lambda x: -x[1])
    linked = 0
    for event in app.execute("SELECT id, summary, detail FROM event WHERE id LIKE 'wiki-%'").fetchall():
        text = (event["summary"] or "") + (event["detail"] or "")
        found = []
        for name, length in names:
            if length < 2:
                continue
            if name in text and name not in found:
                found.append(name)
            if len(found) >= 8:
                break
        if found:
            app.execute("UPDATE event SET participants = ? WHERE id = ?", ("、".join(found), event["id"]))
            linked += 1
    print(f"事件补人物 {linked} 条。", flush=True)

    app.commit()
    counts = app.execute("SELECT category, COUNT(*) FROM person GROUP BY category ORDER BY 2 DESC").fetchall()
    print("最终分类：", {r[0]: r[1] for r in counts}, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
