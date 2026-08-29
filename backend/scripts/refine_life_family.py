#!/usr/bin/env python3
"""生平/家族两栏内容精炼（对全部人物生效）。

规则：
- 生平只保留叙事性段落： cut 参考文献注释、影视艺术形象、流行文化、评价影响等
  非生平段落；删除名片式元数据行（“谥号：……”“最高官职：……”）；删除
  “据哈佛 CBDB”注释行；跳过条目内“生平”同名小标题。
- “家庭/家族/子嗣/亲属/后裔/世系”段落整体移入家族栏（家族栏目为机器生成或
  占位者直接合并；人工校订的 56 位核心栏目保持不动）。
- 〔《明史》原文〕块原样保留在生平末尾。
- 家族栏目统一改名“家族”（App 端同步）。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

MACHINE_MARKS = ("以上为", "史料未见详载", "关系网络所载", "亲属名录据")
HEADER_DROP = {
    "参考文献", "参考资料", "注释", "备注", "外部链接", "参见", "延伸阅读", "书目", "引用",
    "影视形象", "艺术形象", "流行文化", "影视", "衍生作品", "评价", "影响", "后世",
    "纪念", "争议", "轶事", "相关条目",
}
FAMILY_MOVE = ("家庭", "家族", "子嗣", "亲属", "后裔", "后人", "世系", "婚姻")
META_LINE = re.compile(
    r"^(本名|别名|全名|字|号|尊号|庙号|谥号|追赠|封号|年号|政权|民族族群|信仰|王朝|所处时代|"
    r"出生地|出生日期|逝世日期|逝世地|陵墓|安葬地|在位时间|前任|继任|继承者|主要成就|主要作品|"
    r"最高官职|重要事件|相关人物|墓地|墓葬|亲属|爵位|位号|封地)"
    r"[：:]"
)
CBDB_LINE = re.compile(r"据哈佛 CBDB")
ERA_LINE = re.compile(r"^所处时代为")
LIFE_LIMIT = 6000


def is_header(line: str) -> bool:
    return 0 < len(line) <= 20 and not re.search(r"[。！？；：,，]", line)


def clean_lines(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        line = line.strip()
        if not line or META_LINE.match(line) or CBDB_LINE.search(line) or ERA_LINE.match(line):
            continue
        if line == "生平":
            continue
        out.append(line)
    return out


def segment(text: str) -> tuple[list[str], list[tuple[str, list[str]]], bool]:
    """返回 (导语段, [(小标题, 段落行)], 是否截到参考文献)"""
    lines = [l.strip() for l in text.split("\n")]
    lead: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_header: str | None = None
    current: list[str] = []
    truncated = False
    for line in lines:
        if not line:
            continue
        if is_header(line) and not re.search(r"[）)」」\d]$", line):
            if current_header is None:
                lead = current
            else:
                sections.append((current_header, current))
            current_header, current = line, []
            continue
        current.append(line)
    if current_header is None:
        lead = current
    else:
        sections.append((current_header, current))
    return lead, sections, truncated


def main() -> int:
    app = sqlite3.connect(BACKEND / "data" / "ming_history.sqlite3")
    app.row_factory = sqlite3.Row

    lives = {r["person_id"]: r["content"] for r in app.execute("SELECT person_id, content FROM person_section WHERE section_key='life'")}
    families = {r["person_id"]: r["content"] for r in app.execute("SELECT person_id, content FROM person_section WHERE section_key='family'")}

    def segment(text: str):
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        lead: list[str] = []
        sections: list[tuple[str, list[str]]] = []
        header = None
        cur: list[str] = []
        for line in lines:
            if is_header(line) and not re.search(r"[）)」\d]$", line) and not line.startswith("〔"):
                if header is None:
                    lead = cur
                else:
                    sections.append((header, cur))
                header, cur = line, []
                continue
            cur.append(line)
        if header is None:
            lead = cur
        else:
            sections.append((header, cur))
        return lead, sections

    life_fixed = family_fixed = 0
    for pid, content in lives.items():
        if not content:
            continue
        # 《明史》原文块拆出，末尾原样保留
        shi_block = ""
        modern = content
        if "〔《明史》原文" in modern:
            idx = modern.index("〔《明史》原文")
            shi_block = modern[idx:].strip()
            modern = modern[:idx].strip()

        lead, sections = segment(modern)
        kept: list[str] = []
        family_blocks: list[str] = []
        for header, body in sections:
            if any(header.startswith(h) for h in FAMILY_MOVE):
                family_blocks += body
                continue
            if header in HEADER_DROP or any(header.startswith(h) for h in ("参考文献", "注释", "外部链接", "参见", "延伸阅读", "影视", "艺术", "流行")):
                continue
            kept += [header] + body

        new_life_lines = clean_lines(lead) + clean_lines(kept)
        new_life = "\n\n".join(new_life_lines)[:LIFE_LIMIT]
        if shi_block:
            new_life = (new_life + "\n\n" if new_life else "") + shi_block
        if new_life != content:
            app.execute("UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'life'", (new_life, pid))
            life_fixed += 1

        # 家庭/子嗣段落移入家族栏（人工校订栏目不动）
        cur_fam = families.get(pid, "") or ""
        is_curated = bool(cur_fam) and not any(m in cur_fam for m in MACHINE_MARKS)
        if family_blocks and not is_curated:
            moved = clean_lines(family_blocks)
            if moved:
                new_fam = (cur_fam + "\n" if cur_fam else "") + "\n".join(moved)
                db_fam = families.get(pid, "")
                app.execute("UPDATE person_section SET content = ? WHERE person_id = ? AND section_key = 'family'", (new_fam, pid))
                app.execute("UPDATE person SET family_summary = ? WHERE id = ?", (new_fam, pid))
                family_fixed += 1

    # 栏目名统一“家族”
    app.execute("UPDATE person_section SET title = '家族' WHERE section_key = 'family'")
    app.commit()
    print(f"生平精炼 {life_fixed} 位；家庭段落并入家族 {family_fixed} 位；栏目名统一“家族”。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
