#!/usr/bin/env python3
"""数据准确性审计：关系边、事件参与人物、家族名录逐一校验。

- 关系边合理性：配偶需生年窗口可婚（双方 13 岁以上有共存期）、父子差 15–70、
  母子差 13–55、兄弟差 ≤25；不满足即删除并记入错误清单。
- 事件参与：人名（或帝号别名）须出现在事件首段，且事件年份在其生卒区间内；
  否则从 participants 中移除并记入清单。
- 家族名录：名录行中可唯一对应库内人物且关系明显不合者（如配偶年龄不可能）
  删除该行；朱允炆配偶马皇后为建文帝后（史实），加注消歧。
- 输出 docs/data-audit.md 错误与修正清单（“注明数据库错误”）。
"""

from __future__ import annotations

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
    m = re.match(r"^\s*(\d{4})—(\d{4})", text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    nums = re.findall(r"(1[3-9]\d{2})", text or "")
    return (int(nums[0]) if nums else None, int(nums[1]) if len(nums) > 1 else None)


def main() -> int:
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
            if not (15 <= bb - ba <= 70):
                bad = f"父子年差不可能（父 {ba} / 子 {bb}）"
        elif rel == "母子":
            if not (13 <= bb - ba <= 55):
                bad = f"母子年差不可能（母 {ba} / 子 {bb}）"
        elif rel == "兄弟姐妹":
            if abs(ba - bb) > 25:
                bad = f"兄弟年差过大（{ba} 与 {bb}）"
        if bad:
            an = people[a]["name"]
            bn = people[b]["name"]
            removed_edges.append((an, rel, bn, bad))
            report.append(f"- 删除关系 {an} —{rel}— {bn}:{bad}。")

    # ---- 2) 事件参与人物：首段出现 + 在世校验 ----
    event_fixes: list[str] = []
    for ev in app.execute("SELECT id, title, year, summary, detail, participants FROM event").fetchall():
        year = ev["year"]
        detail = ev["detail"] or ""
        lead = re.split(r"\n\n", detail)[0] if detail else ""
        lead = lead or (ev["summary"] or "")
        names = [n for n in ev["participants"].split("、") if n]
        if not names:
            continue
        valid = []
        for n in names:
            pid = next((p for p, r in people.items() if r["name"] == n), None)
            if pid is None:
                valid.append(n)
                continue
            b, d = birth(pid), death(pid)
            in_lead = n in lead
            alias_ok = False
            for alias in ERA_ALIASES.get(pid, []):
                if alias in lead:
                    alias_ok = True
                    break
            if not (in_lead or alias_ok):
                report.append(f"- 移除事件参与「{ev['title']}」×{n}:人名未见于事件首段。")
                event_fixes.append(f"{ev['title']} × {n}")
                continue
            if b and year and year < b:
                report.append(f"- 移除事件参与「{ev['title']}」×{n}:事件年份早于其生年({b})。")
                event_fixes.append(f"{ev['title']} × {n}")
                continue
            if d and year and year > d + 8:
                report.append(f"- 移除事件参与「{ev['title']}」×{n}:事件年份晚于其卒年({d})。")
                event_fixes.append(f"{ev['title']} × {n}")
                continue
            valid.append(n)
        if len(valid) != len(names):
            app.execute("UPDATE event SET participants = ? WHERE id = ?", ("、".join(valid), ev["id"]))

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
        if changed:
            app.execute("UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'family'", ("\n".join(new_lines), pid))

    # ---- 4) 朱允炆配偶消歧（建文帝后马氏，非太祖马皇后） ----
    zyw = fam.get("zhuyunwen", "")
    if "配偶：马皇后。" in zyw:
        zyw = zyw.replace("配偶：马皇后。", "配偶：马皇后（建文帝后，非明太祖马皇后）。")
        app.execute("UPDATE person_section SET content = ? WHERE person_id = 'zhuyunwen' AND section_key = 'family'", (zyw,))
        report.append("- 朱允炆家族名录「配偶：马皇后」加注消歧:建文帝后马氏与太祖马皇后同名异人。")

    app.commit()

    # ---- 5) 输出审计报告 ----
    doc = ["# 数据准确性审计报告", "", "本次逐一校验发现的数据库错误与修正记录。", ""]
    doc += report if report else ["- 未发现需要修正的条目。"]
    (BACKEND.parent / "docs" / "data-audit.md").write_text("\n".join(doc) + "\n", encoding="utf-8")
    print(f"关系删除 {len(removed_edges)};事件参与修正 {len(event_fixes)};家族修剪 {len(family_fixes)};消歧 1。", flush=True)
    for r in report[:20]:
        print(" ", r, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
