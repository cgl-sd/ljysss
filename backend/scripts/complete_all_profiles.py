#!/usr/bin/env python3
"""收尾补全：让资料库内全部人物都有“生平”与“家族”栏目。

- life：无生平栏目的人物，用《明史》传文（已有索引者）或既有简介补齐；
  王振、黄淮的简介曾被同名错撞污染（女演员/地理区域），此处一并修正。
- family：无家族栏目的人物，先从既有关系边反推亲属名录（父子/母子/
  配偶/兄弟姐妹双向），确无资料者写明“史料未详”的诚实占位。

56 位核心人物的人工校订栏目保持不动。
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import connect, initialize_database  # noqa: E402

# 手工校订：曾被同名错撞污染或需要精确表述的简介。
MANUAL_BIO = {
    "wangzhen": "王振（？—1449），蔚州（今河北蔚县）人，明英宗朝司礼监掌印太监。早年自阉入宫，侍英宗于东宫，英宗即位后掌司礼监，干预朝政，开明代宦官专权之局。正统十四年（1449）怂恿英宗亲征瓦剌，行军调度失宜，土木之变中为乱军所杀。英宗复辟后为其立旌忠祠，天顺间事。",
    "huanghuai": "黄淮（1367—1449），字宗豫，温州永嘉人。洪武三十年（1397）进士，授中书舍人。永乐间与解缙、杨士奇等同直文渊阁，预机务，官至武英殿大学士。永乐十二年受汉王构陷下诏狱，系十年，仁宗即位复官。洪熙、宣德间以老疾致仕，归里十四年，正统十四年卒，谥文简。",
}
MANUAL_FAMILY = {
    "wangzhen": "侄王山：倚振势官锦衣卫，振死后伏诛。",
    "zhoutaihou": "父亲：周龙，以女贵追封庆云侯。\n兄弟：周寿（庆云侯）、周彧（长宁伯）。\n儿子：明宪宗朱见深。",
    "wanguifei": "父亲：万贵，本为县吏，坐事谪居霸州，以女贵起复。\n兄弟：万喜等骤授锦衣卫官职，骄横一时；贵妃崩后家势遂衰。",
    "jishufei": "家族原籍广西贺县。\n孝宗即位后追尊太后，遣使访求母族，官为抚恤。",
    "lixuanshi": "儿子：怀惠王朱由模。\n女儿：乐安公主朱徽媞。\n抚养明熹宗、明思宗兄弟。",
    "tianguifei": "父亲：田弘遇，以女贵官左都督，京师号“田戚畹”。\n儿子：永王朱慈炤、悼灵王朱慈焕等。",
    "zhuzaihe": "父亲：明世宗朱厚熜。\n母亲：王贵妃。\n弟弟：明穆宗朱载坖等。",
    "zhuyoubin": "父亲：明宪宗朱见深。\n儿子：益庄王朱厚烨，子孙袭封益王至明末。",
    "zhuyouhui": "父亲：明宪宗朱见深。\n封淮王，就藩饶州，子孙袭封至明末，谥靖。",
    "zhengzhilong": "儿子：郑成功（郑森）。\n诸弟郑芝虎、郑鸿逵等分领海上兵力。",
    "xuhuanghou": "父亲：徐达，中山王。\n儿子：明仁宗朱高炽、汉王朱高煦、赵王朱高燧。",
}


def main() -> int:
    initialize_database()
    with connect() as db:
        people = db.execute("SELECT id, name, biography, family_summary FROM person ORDER BY id").fetchall()
        mingshi = {
            row["person_id"]: (row["excerpt"], row["kind"], row["juan"])
            for row in db.execute("SELECT person_id, excerpt, kind, juan FROM person_mingshi")
        }
        curated_family = {
            row["person_id"]
            for row in db.execute("SELECT person_id FROM person_section WHERE section_key = 'family' AND length(trim(content)) > 0")
        }
        curated_life = {
            row["person_id"]
            for row in db.execute("SELECT person_id FROM person_section WHERE section_key = 'life'")
        }
        # 关系边 → 亲属名录
        edges = db.execute(
            "SELECT from_person_id, to_person_id, relation_type FROM person_relation"
        ).fetchall()
        person_names = {row["id"]: row["name"] for row in db.execute("SELECT id, name FROM person")}

    family_from_edges: dict[str, list[str]] = {}
    for edge in edges:
        a, b, rel = edge["from_person_id"], edge["to_person_id"], edge["relation_type"]
        a_name, b_name = person_names.get(a, a), person_names.get(b, b)
        if rel == "父子":
            family_from_edges.setdefault(a, []).append(f"儿子：{b_name}。")
            family_from_edges.setdefault(b, []).append(f"父亲：{a_name}。")
        elif rel == "母子":
            family_from_edges.setdefault(a, []).append(f"儿子：{b_name}。")
            family_from_edges.setdefault(b, []).append(f"母亲：{a_name}。")
        elif rel == "配偶":
            family_from_edges.setdefault(a, []).append(f"配偶：{b_name}。")
            family_from_edges.setdefault(b, []).append(f"配偶：{a_name}。")
        elif rel == "兄弟姐妹":
            family_from_edges.setdefault(a, []).append(f"兄弟姐妹：{b_name}。")
            family_from_edges.setdefault(b, []).append(f"兄弟姐妹：{a_name}。")

    life_written = family_written = 0
    with connect() as db:
        for person in people:
            person_id = person["id"]

            # ---- 生平 ----
            if person_id not in curated_life:
                bio = MANUAL_BIO.get(person_id) or (person["biography"] or "").strip()
                parts = []
                if bio:
                    parts.append(bio)
                if person_id in mingshi:
                    excerpt, kind, juan = mingshi[person_id]
                    parts.append(f"〔《明史》原文·{kind}卷{juan}〕\n{excerpt}")
                if parts:
                    content = "\n\n".join(parts)
                    db.execute(
                        """
                        INSERT INTO person_section(person_id, section_key, title, position, content)
                        VALUES (?, 'life', '生平', 0, ?)
                        ON CONFLICT(person_id, section_key) DO UPDATE SET content = excluded.content
                        """,
                        (person_id, content),
                    )
                    if person_id in MANUAL_BIO:
                        db.execute("UPDATE person SET biography = ?, summary = ? WHERE id = ?", (content.split("〔《明史》原文〕")[0].strip(), content.split("〔《明史》原文〕")[0].strip()[:80], person_id))
                    life_written += 1

            # ---- 家族与子嗣 ----
            if person_id not in curated_family and person_id not in MANUAL_FAMILY:
                lines = sorted(set(family_from_edges.get(person_id, [])))
                if lines:
                    lines.append("以上为关系网络所载亲属；结局与细节待逐条编核。")
                else:
                    lines = ["其家世与亲属，现存史料未见详载。"]
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

        # 手工家族名录（16 人收尾，核心人物除外）
        for person_id, content in MANUAL_FAMILY.items():
            row = db.execute("SELECT 1 FROM person WHERE id = ?", (person_id,)).fetchone()
            if not row or person_id in curated_family:
                continue
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

        stats = db.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM person) AS people,
              (SELECT COUNT(DISTINCT person_id) FROM person_section WHERE section_key = 'life') AS life,
              (SELECT COUNT(DISTINCT person_id) FROM person_section WHERE section_key = 'family') AS family
            """
        ).fetchone()
    print(f"生平补写 {life_written} 位，家族补写 {family_written} 位。", flush=True)
    print(f"现状：人物 {stats['people']}，有生平 {stats['life']}，有家族 {stats['family']}。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
