#!/usr/bin/env python3
"""数据准确性审计：关系边、事件参与人物、家族名录逐一校验。

- 关系边合理性：配偶需生年窗口可婚（双方 13 岁以上有共存期）；亲子关系不假定
  数据的 from/to 方向，按绝对年差校验；兄弟只在差距确实不可能时提示。
- 事件参与：人名（或帝号别名）须出现在事件五个正文栏，且事件年份在可考生卒区间内；
  否则从正式 event_participant 关联中移除并记入清单。
- 家族名录：名录行中可唯一对应库内人物且关系明显不合者（如配偶年龄不可能）
  删除该行；朱允炆配偶马皇后为建文帝后（史实），加注消歧。
- 默认只输出结果，不改数据库或项目文档；只有显式传 --apply 才会修改库。
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

from opencc import OpenCC

t2s = OpenCC("t2s")  # noqa
s2t = OpenCC("s2t")

ERA_ALIASES = {
    "zhuyousong": ["弘光帝", "明安宗"],
    "zhuyujian": ["隆武帝", "明绍宗"],
    "zhuyuyu": ["绍武帝"],
    "zhuyoulang": ["永历帝", "永曆帝", "明昭宗"],
    "zhuqiyu": ["景泰帝", "明代宗", "建文帝" if False else "景帝"],
    "zhuqizhen": ["正统帝", "天顺帝", "英宗"],
    "zhuyunwen": ["建文帝", "惠帝"],
    "zhuyoujian": ["崇祯帝", "庄烈帝"],
    "zhuhoucong": ["嘉靖帝"],
    "zhuyijun": ["万历帝"],
    "zhudi": ["永乐帝", "成祖"],
    "zhugaochi": ["洪熙帝"],
    "zhuzhanji": ["宣德帝"],
    "zhuqizhen": ["英宗"],
    "zhujian": ["成化帝"],
    "zhuyoutang": ["弘治帝"],
    "zhuhouzhao": ["正德帝"],
    "zhuzaihou": ["隆庆帝"],
    "zhuchangluo": ["泰昌帝"],
    "zhuyouxiao": ["天启帝"],
    "zhuyuanzhang": ["洪武帝", "太祖"],
}


def years_of(text: str) -> tuple[int | None, int | None]:
    # Only a complete printed lifespan can support date-window rejection.  A
    # display such as "？—1393" gives a death year, not a fictional 1393 birth.
    m = re.match(r"^\s*(\d{4})\s*[—-]\s*(\d{4})", text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser(description="校验人物关系、事件参与者与家族名录。默认只读。")
    parser.add_argument("--apply", action="store_true", help="确认后才把无效数据从 SQLite 删除；随后应 export 回 JSONL。")
    args = parser.parse_args()
    app = sqlite3.connect(BACKEND / "data" / "ming_history.sqlite3")
    app.row_factory = sqlite3.Row

    people = {r["id"]: r for r in app.execute("SELECT id, name, title, category, years, biography FROM person")}
    life = {r["person_id"]: r["content"] for r in app.execute("SELECT person_id, content FROM person_section WHERE section_key='life'")}
    fam = {r["person_id"]: r["content"] for r in app.execute("SELECT person_id, content FROM person_section WHERE section_key='family'")}
    reigns = {r["title"]: (r["start_year"], r["end_year"]) for r in app.execute("SELECT title, start_year, end_year FROM reign")}

    def birth(pid: str) -> int | None:
        return years_of(people[pid]["years"])[0] if pid in people else None

    def death(pid: str) -> int | None:
        return years_of(people[pid]["years"])[1] if pid in people else None

    report: list[str] = []

    # ---- 1) 关系边合理性 ----
    removed_edges: list[tuple[str, str, str, str]] = []
    for e in app.execute("SELECT from_person_id, to_person_id, relation_type, note FROM person_relation").fetchall():
        a, b, rel = e["from_person_id"], e["to_person_id"], e["relation_type"]
        ba, da = birth(a), death(a)
        bb, db = birth(b), death(b)
        bad = None
        if None in (ba, bb) or None in (da, db):
            continue
        if rel == "配偶":
            if max(ba, bb) + 13 > min(da, db):
                bad = f"婚龄窗口不可能（{ba}—{da} 与 {bb}—{db}）"
        elif rel == "父子":
            if not (15 <= abs(bb - ba) <= 70):
                bad = f"父子年差不可能（{ba} 与 {bb}）"
        elif rel == "母子":
            if not (13 <= abs(bb - ba) <= 55):
                bad = f"母子年差不可能（{ba} 与 {bb}）"
        elif rel == "兄弟姐妹":
            if abs(ba - bb) > 45:
                bad = f"兄弟年差过大（{ba} 与 {bb}）"
        if bad:
            an = people[a]["name"]
            bn = people[b]["name"]
            removed_edges.append((an, rel, bn, bad))
            action = "删除" if args.apply else "待删除"
            report.append(f"- {action}关系 {an} —{rel}— {bn}:{bad}。")
            if args.apply:
                app.execute(
                    "DELETE FROM person_relation WHERE from_person_id = ? AND to_person_id = ? AND relation_type = ? AND note = ?",
                    (a, b, rel, e["note"]),
                )

    # ---- 2) 事件参与人物：五个正文栏具名出现 + 在世校验 ----
    event_fixes: list[str] = []
    event_bodies = {
        row["event_id"]: row["body"]
        for row in app.execute(
            "SELECT event_id, GROUP_CONCAT(content, char(10)) AS body FROM event_section GROUP BY event_id"
        ).fetchall()
    }
    event_people: dict[str, list[tuple[str, str]]] = {}
    for row in app.execute(
        """
        SELECT ep.event_id, ep.person_id, p.name
        FROM event_participant AS ep
        JOIN person AS p ON p.id = ep.person_id
        ORDER BY ep.event_id, ep.rowid
        """
    ).fetchall():
        event_people.setdefault(row["event_id"], []).append((row["person_id"], row["name"]))
    for ev in app.execute("SELECT id, title, year FROM event").fetchall():
        year = ev["year"]
        body = event_bodies.get(ev["id"], "")
        for pid, n in event_people.get(ev["id"], []):
            b, d = birth(pid), death(pid)
            in_body = n in body
            alias_ok = False
            for alias in ERA_ALIASES.get(pid, []):
                if alias in body:
                    alias_ok = True
                    break
            if not (in_body or alias_ok):
                action = "移除" if args.apply else "待移除"
                report.append(f"- {action}事件参与「{ev['title']}」×{n}:姓名未见于事件正文。")
                event_fixes.append(f"{ev['title']} × {n}")
                if args.apply:
                    app.execute("DELETE FROM event_participant WHERE event_id = ? AND person_id = ?", (ev["id"], pid))
                continue
            if b and year and year < b:
                action = "移除" if args.apply else "待移除"
                report.append(f"- {action}事件参与「{ev['title']}」×{n}:事件年份早于其生年({b})。")
                event_fixes.append(f"{ev['title']} × {n}")
                if args.apply:
                    app.execute("DELETE FROM event_participant WHERE event_id = ? AND person_id = ?", (ev["id"], pid))
                continue
            if d and year and year > d + 8:
                action = "移除" if args.apply else "待移除"
                report.append(f"- {action}事件参与「{ev['title']}」×{n}:事件年份晚于其卒年({d})。")
                event_fixes.append(f"{ev['title']} × {n}")
                if args.apply:
                    app.execute("DELETE FROM event_participant WHERE event_id = ? AND person_id = ?", (ev["id"], pid))

    # ---- 3) 家族名录修剪：可解析且明显不合的亲属行 ----
    family_fixes: list[str] = []
    for pid, content in fam.items():
        if not content:
            continue
        person = people.get(pid)
        if not person:
            continue
        b, d = years_of(person["years"])
        lines = content.split("\n")
        new_lines = []
        changed = False
        for line in lines:
            m = re.match(r"^(配偶|兄弟姐妹)：([、\u4e00-\u9fa5]+)。$", line)
            drop = False
            if m and b and d:
                kind, names = m.group(1), m.group(2).split("、")
                for n in names:
                    pid2 = next((q for q, r in people.items() if r["name"] == n), None)
                    if pid2 is None:
                        continue
                    b2, d2 = years_of(people[pid2]["years"])
                    if None in (b2, d2, b, d):
                        continue
                    if kind == "配偶" and max(b, b2) + 13 > min(d, d2):
                        drop = True
                        report.append(f"- 删除 {person['name']} 家族名录配偶行「{n}」:婚龄窗口不可能。")
                        family_fixes.append(f"{person['name']} × 配偶 {n}")
                    if kind == "兄弟姐妹" and abs(b - b2) > 25:
                        drop = True
                        report.append(f"- 删除 {person['name']} 家族名录兄弟行「{n}」:年差过大。")
                        family_fixes.append(f"{person['name']} × 兄弟 {n}")
            if drop:
                changed = True
                continue
            new_lines.append(line)
        if changed and args.apply:
            app.execute("UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'family'", ("\n".join(new_lines), pid))

    # ---- 4) 朱允炆配偶消歧（建文帝后马氏，非太祖马皇后） ----
    zyw = fam.get("zhuyunwen", "")
    if args.apply and "配偶：马皇后。" in zyw:
        zyw = zyw.replace("配偶：马皇后。", "配偶：马皇后（建文帝后，非明太祖马皇后）。")
        app.execute("UPDATE person_section SET content = ? WHERE person_id = 'zhuyunwen' AND section_key = 'family'", (zyw,))
        report.append("- 朱允炆家族名录「配偶：马皇后」加注消歧:建文帝后马氏与太祖马皇后同名异人。")

    if args.apply:
        # event.participants is retained for legacy readers, but must mirror the
        # authoritative event_participant rows after an explicit correction.
        for event_id, names in app.execute(
            """
            SELECT ep.event_id, GROUP_CONCAT(p.name, '、')
            FROM event_participant AS ep
            JOIN person AS p ON p.id = ep.person_id
            GROUP BY ep.event_id
            """
        ).fetchall():
            app.execute("UPDATE event SET participants = ? WHERE id = ?", (names, event_id))
        app.commit()

    mode = "已应用" if args.apply else "只读"
    print(f"{mode}：关系问题 {len(removed_edges)}；事件参与问题 {len(event_fixes)}；家族问题 {len(family_fixes)}。", flush=True)
    for r in report[:20]:
        print(" ", r, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
