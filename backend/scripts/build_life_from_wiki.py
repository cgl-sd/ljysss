#!/usr/bin/env python3
"""从 HuggingFace 国内镜像的维基百科数据包（20231101.zh，6 个 parquet）
提取目标人物的完整条目文本，写入“生平”栏目。

- 标题匹配：人名简繁双形 + 庙号/帝号别名（明成祖、建文帝、弘光帝……）。
- 生平栏目：条目全文（上限 8000 字，句界截断）置于最前，
  〔《明史》原文〕块原样保留在其后。
- 有维基条目即按项目规则标“已校验”，并在 content_reference 记录出处（CC BY-SA）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

import pyarrow.parquet as pq  # noqa: E402
from opencc import OpenCC  # noqa: E402

from app.database import connect, initialize_database  # noqa: E402

PACK_DIR = Path("/tmp/wikihf")
PACKS = [PACK_DIR / f"train-0000{i}.parquet" for i in range(6)]
LIFE_LIMIT = 8000
s2t = OpenCC("s2t")

# 南明帝王与特殊帝号的维基标题别名
EXTRA_ALIASES = {
    "zhuyousong": ["弘光帝", "明安宗"],
    "zhuyujian": ["隆武帝", "明绍宗"],
    "zhuyuyu": ["绍武帝", "紹武帝"],
    "zhuyoulang": ["永历帝", "永曆帝", "明昭宗"],
    "zhuqiyu": ["景泰帝", "明代宗", "明景帝"],
    "zhuqizhen": ["天顺帝", "正統帝", "正统帝"],
    "zhuyunwen": ["建文帝"],
    "zhuyoujian": ["崇祯帝", "崇禎帝", "庄烈帝", "莊烈帝"],
    "zhuhoucong": ["嘉靖帝", "世宗肅皇帝"],
    "zhuyijun": ["万历帝", "萬曆帝"],
    "zhuyuanzhang": ["洪武帝", "洪武帝"],
}


# 词条标题变体：异体字与谥号/封号命名（人工核对）
MANUAL_TITLES = {
    "gaoqi": ["高啟"],
    "luxiangsheng": ["盧象昇", "盧象升"],
    "gaogu": ["高穀"],
    "lutan": ["盧柟"],
    "xuzan": ["許讚"],
    "zhangcai": ["張綵"],
    "liuting": ["劉綎", "劉鋌"],
    "xuhuanghou": ["仁孝文皇后"],
    "sunhuanghou": ["孝恭章皇后"],
    "tianguifei": ["田秀英"],
    "jishufei": ["孝穆紀太后", "孝穆纪太后"],
    "zhoutaihou": ["孝肅周太后", "孝肃周太后"],
    "fanghuanghou": ["孝烈方皇后", "孝烈皇后"],
    "lixuanshi": ["李選侍", "李康妃"],
    "zhuyouhui": ["朱祐楎"],
    "zhuzaihe": ["朱載壡", "莊敬太子"],
    "zhuyuhao": ["定武帝", "紹武帝"],
    "chenlin": ["陳璘"],
    "yuxian": ["于謙"],
    "wangzhen": ["王振 (明朝)"],
    "huanghuai": ["黃淮"],
    "guoningfei": ["郭寧妃"],
    "zhenghe": ["鄭和"],
    "qijiguang": ["戚繼光"],
    "xiongtingbi": ["熊廷弼"],
    "wangshouren": ["王陽明"],
    "lishizhen": ["李時珍"],
    "zhengchenggong": ["鄭成功"],
    "zhanghuangyan": ["張煌言"],
    "hongchengchou": ["洪承疇"],
}


def alias_forms(person) -> list[str]:
    forms = []
    for base in (person["name"], s2t.convert(person["name"])):
        forms.append(base)
    title = person["title"] or ""
    for token in re.split(r"[·・／/()（）、]", title):
        token = token.strip()
        if 2 <= len(token) <= 8 and ("帝" in token or "王" in token or token.startswith("明")):
            forms.extend((token, s2t.convert(token)))
    for alias in EXTRA_ALIASES.get(person["id"], []) + MANUAL_TITLES.get(person["id"], []):
        forms.extend((alias, s2t.convert(alias)))
    return list(dict.fromkeys(f for f in forms if f))


def main() -> int:
    initialize_database()
    with connect() as db:
        people = db.execute("SELECT id, name, title, category FROM person ORDER BY id").fetchall()
        life_now = {
            row["person_id"]: row["content"]
            for row in db.execute("SELECT person_id, content FROM person_section WHERE section_key = 'life'")
        }

    # 标题 → (person, form)
    title_map: dict[str, tuple[str, str]] = {}
    for person in people:
        for form in alias_forms(person):
            key = form.replace(" ", "_")
            if key not in title_map:
                title_map[key] = (person["id"], form)

    texts: dict[str, tuple[str, str]] = {}
    for pack in PACKS:
        table = pq.read_table(str(pack), columns=["title", "text"])
        for title, text in zip(table.column("title").to_pylist(), table.column("text").to_pylist()):
            hit = title_map.get(title)
            if hit and hit[0] not in texts:
                texts[hit[0]] = (title, text)
    print(f"维基全文命中 {len(texts)}/748 人。", flush=True)

    written = verified = 0
    with connect() as db:
        for person in people:
            person_id = person["id"]
            if person_id not in texts:
                continue
            wiki_title, text = texts[person_id]
            trimmed = text.strip()
            if len(trimmed) > LIFE_LIMIT:
                trimmed = trimmed[:LIFE_LIMIT].rsplit("。", 1)[0] + "。"
            current = life_now.get(person_id, "")
            shi_block = ""
            if "〔《明史》原文" in current:
                shi_block = current[current.index("〔《明史》原文"):].strip()
            content = trimmed + ("\n\n" + shi_block if shi_block else "")
            db.execute(
                """
                INSERT INTO person_section(person_id, section_key, title, position, content)
                VALUES (?, 'life', '生平', 0, ?)
                ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content
                """,
                (person_id, content),
            )
            db.execute("UPDATE person SET verification_status = '已校验' WHERE id = ?", (person_id,))
            db.execute(
                """
                INSERT INTO content_reference(content_type, content_id, section_key, position, title, url, locator, note)
                VALUES ('person', ?, 'life', 0, '中文维基百科条目', ?, ?, '官方数据包提取，CC BY-SA')
                ON CONFLICT(content_type, content_id, section_key, position) DO UPDATE SET
                    title = excluded.title, url = excluded.url, locator = excluded.locator, note = excluded.note
                """,
                (person_id, f"https://zh.wikipedia.org/wiki/{wiki_title}", wiki_title),
            )
            written += 1
            verified += 1

        total_verified = db.execute("SELECT COUNT(*) FROM person WHERE verification_status = '已校验'").fetchone()[0]
        misses = [p["name"] for p in people if p["id"] not in texts]
    print(f"生平重写 {written} 位；全库已校验 {total_verified} 位。", flush=True)
    print(f"未命中 {len(misses)} 位：{misses}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
