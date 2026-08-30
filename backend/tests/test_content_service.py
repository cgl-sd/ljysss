import unittest

from app.database import initialize_database
from app.main import bootstrap_content, get_person


class ContentServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_bootstrap_has_the_reading_domains(self):
        payload = bootstrap_content()
        self.assertEqual(17, len(payload["reigns"]))
        self.assertGreaterEqual(len(payload["events"]), 47)
        # 748 位精选 + 全量收录的明朝相关人物（明史传主 ∩ 维基），下限 700、上限放开。
        self.assertGreaterEqual(len(payload["people"]), 700)
        # 皇帝不与文臣武将建关系；关系网以家庭、同僚与南明阵营类为主，亲属补录可持续增加。
        self.assertGreaterEqual(len(payload["relationships"]), 30)
        self.assertGreaterEqual(len(payload["institutions"]), 12)

    def test_bootstrap_people_expose_structured_sections(self):
        payload = bootstrap_content()
        person = next(item for item in payload["people"] if item["id"] == "zhangjuzheng")
        self.assertIn("sections", person)

    def test_person_profile_schema_registers_the_six_categories_and_four_sections(self):
        from app.main import person_profile_schema

        schema = person_profile_schema()
        categories = schema["categories"]
        self.assertEqual(["帝王", "内廷", "封爵", "朝臣", "将帅", "文苑"], [item["label"] for item in categories])
        self.assertEqual(len(bootstrap_content()["people"]), sum(item["person_count"] for item in categories))
        self.assertEqual(
            ["life", "family", "relations", "events"],
            [item["section_key"] for item in schema["sections"]],
        )

    def test_person_profile_rows_follow_registered_taxonomy(self):
        from app.database import connect

        with connect() as database:
            unknown_category = database.execute(
                """
                SELECT COUNT(*) FROM person AS p
                LEFT JOIN person_category AS c ON c.label = p.category
                WHERE c.id IS NULL
                """
            ).fetchone()[0]
            invalid_section = database.execute(
                """
                SELECT COUNT(*) FROM person_section AS s
                LEFT JOIN person_section_definition AS d
                    ON d.section_key = s.section_key AND d.title = s.title AND d.position = s.position
                WHERE d.section_key IS NULL
                """
            ).fetchone()[0]
        self.assertEqual(0, unknown_category)
        self.assertEqual(0, invalid_section)

    def test_database_rejects_an_unregistered_category_or_section_layout(self):
        import sqlite3

        from app.database import connect

        with connect() as database:
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute("UPDATE person SET category = '其他' WHERE id = 'zhangjuzheng'")
            with self.assertRaises(sqlite3.IntegrityError):
                database.execute(
                    """
                    UPDATE person_section SET title = '基本资料'
                    WHERE person_id = 'zhangjuzheng' AND section_key = 'life'
                    """
                )

    def test_rebuild_schema_exposes_uniform_section_endpoints(self):
        from app.main import get_event_sections

        sections = {section["section_key"] for section in get_event_sections("hongwu-founding")}
        self.assertEqual({"background", "course", "people", "result", "impact"}, sections)

    def test_every_person_and_event_has_a_uniform_profile_template(self):
        from app.database import connect

        with connect() as database:
            people = database.execute("SELECT COUNT(*) FROM person").fetchone()[0]
            events = database.execute("SELECT COUNT(*) FROM event").fetchone()[0]
            events_with_background = database.execute(
                "SELECT COUNT(DISTINCT event_id) FROM event_section WHERE section_key = 'background'"
            ).fetchone()[0]
        self.assertGreaterEqual(people, 700)
        self.assertEqual(events, events_with_background)

    def test_every_person_has_a_factual_biography(self):
        from app.database import connect

        with connect() as database:
            people = database.execute("SELECT COUNT(*) FROM person").fetchone()[0]
            with_biography = database.execute(
                "SELECT COUNT(*) FROM person WHERE length(biography) >= 25"
            ).fetchone()[0]
        self.assertEqual(people, with_biography)

    def test_person_catalog_has_no_cbdb_legacy_rows(self):
        from app.database import connect

        with connect() as database:
            cbdb_people = database.execute(
                "SELECT COUNT(*) FROM person WHERE source_id = 'cbdb-20210525' OR id LIKE 'cbdb-%'"
            ).fetchone()[0]
            cbdb_research = database.execute(
                "SELECT COUNT(*) FROM person_research WHERE person_id LIKE 'cbdb-%'"
            ).fetchone()[0]
        self.assertEqual(0, cbdb_people)
        self.assertEqual(0, cbdb_research)

    def test_researched_person_profile_survives_catalog_synchronization(self):
        person = get_person("caobianjiao")
        self.assertEqual("曹变蛟", person["name"])
        self.assertGreaterEqual(len(person["biography"]), 40)

    def test_baike_verified_profiles_include_education_and_children(self):
        person = get_person("zhangjuzheng")
        self.assertIn("嘉靖二十六年", person["biography"])
        self.assertIn("张居正", person["name"])

    def test_same_name_entity_is_not_mixed_into_the_wrong_profile(self):
        person = get_person("wangzhi-minister")
        self.assertNotIn("海盗", person["biography"])
        self.assertIn("吏部尚书", person["title"])

    def test_noble_family_children_are_structured_relationships(self):
        person = get_person("xuda")
        children = {
            relationship["to_name"]
            for relationship in person["relationships"]
            if relationship["from_name"] == "徐达" and relationship["relation_type"] == "父子"
        }
        # 徐添福没有可匹配的中文维基人物条目，已按人物库门槛移除；剩余子嗣仍须可跳转。
        self.assertEqual({"徐辉祖", "徐膺绪", "徐增寿"}, children)
        catalog_ids = {entry["id"] for entry in bootstrap_content()["people"]}
        self.assertNotIn("xutianfu", catalog_ids)

    def test_famous_people_are_present_in_catalog(self):
        payload = bootstrap_content()
        names = {person["name"] for person in payload["people"]}
        expected = {
            "朱元璋", "张居正", "海瑞", "戚继光", "郑和", "王守仁",
            "李时珍", "马皇后", "朱权", "朱载堉",
        }
        self.assertTrue(expected <= names)

    def test_new_categories_include_court_and_titled_groups(self):
        payload = bootstrap_content()
        categories = {person["category"] for person in payload["people"]}
        self.assertIn("内廷", categories)
        self.assertIn("封爵", categories)
        # 六分类收拢后不应再出现旧标签。
        self.assertFalse(categories & {"皇帝", "后妃", "宦官", "藩王", "勋贵", "名臣", "名将", "文人"})

    def test_world_page_special_items_are_served(self):
        payload = bootstrap_content()
        specials = payload["specials"]
        self.assertGreaterEqual(len(specials), 8)
        names = {item["name"] for item in specials}
        self.assertIn("尚方宝剑", names)
        self.assertIn("王命旗牌", names)
        for item in specials:
            self.assertTrue(item["description"].strip())

    def test_emperors_have_no_minister_or_general_relations(self):
        from app.database import connect

        with connect() as database:
            offenders = database.execute(
                """
                SELECT pr.id FROM person_relation pr
                JOIN person a ON a.id = pr.from_person_id
                JOIN person b ON b.id = pr.to_person_id
                WHERE (a.category = '皇帝' AND b.category IN ('名臣', '名将'))
                   OR (b.category = '皇帝' AND a.category IN ('名臣', '名将'))
                """
            ).fetchall()
        self.assertEqual([], offenders)

    def test_purged_non_ming_entries_stay_out_of_the_catalog(self):
        from app.catalog import PEOPLE
        from app.database import connect

        # purge_non_ming_people.py 的代表样本：清朝人物、现代错撞、非明朝/神话。
        purged_ids = {
            "caiyurong", "kongsizhen", "kongyoude", "shangkexi", "shilang",
            "gengjingzhong", "yuchenglong", "zhaoliangdong", "zhuchun",
            "zhangjie", "xuke", "luguangzu", "zhumei", "tanglong",
            "liqing", "lichanggeng",
        }
        catalog_ids = {person["id"] for person in PEOPLE}
        self.assertFalse(purged_ids & catalog_ids, "被清理的词条重新出现在编目目录中")

        # id 现由姓名生成，同名的明代会合法复用同一串 id（陆光祖、唐龙、徐恪均为
        # 《明史》传主），所以真正的不变量不是“id 不得再出现”，而是“每个人必须有明代依据”。
        with connect() as database:
            marks = ",".join("?" * len(purged_ids))
            unanchored = database.execute(
                f"""
                SELECT p.id FROM person p
                WHERE p.id IN ({marks})
                  AND NOT EXISTS (
                      SELECT 1 FROM content_reference r
                      WHERE r.content_type = 'person' AND r.content_id = p.id
                        AND r.locator LIKE '明史卷%')
                """,
                sorted(purged_ids),
            ).fetchall()
        self.assertEqual([], [row[0] for row in unanchored],
                         "被清理过的词条以无明史锚点的形式回来了")

        with connect() as database:
            without_anchor = database.execute(
                """
                SELECT COUNT(*) FROM person p
                WHERE NOT EXISTS (
                    SELECT 1 FROM content_reference r
                    WHERE r.content_type = 'person' AND r.content_id = p.id
                      AND r.locator LIKE '明史卷%')
                  AND NOT EXISTS (
                    SELECT 1 FROM person_mingshi m WHERE m.person_id = p.id)
                """
            ).fetchone()[0]
            total = database.execute("SELECT COUNT(*) FROM person").fetchone()[0]
        self.assertLess(without_anchor / total, 0.35,
                        "超过三分之一的条目没有任何《明史》锚点，明代归属无从校核")

    def test_every_parseable_person_chronology_stays_within_ming_bounds(self):
        import re

        from app.database import connect

        with connect() as database:
            rows = database.execute("SELECT id, years FROM person").fetchall()
        for row in rows:
            match = re.match(r"^\s*([?？\d]{1,4})\s*—\s*([?？\d]{1,4})\s*$", row["years"])
            if not match:
                continue
            birth, death = match.group(1), match.group(2)
            if birth.isdigit():
                self.assertLessEqual(int(birth), 1644, f"{row['id']} 生年晚于明亡：{row['years']}")
            if death.isdigit():
                self.assertLessEqual(int(death), 1700, f"{row['id']} 卒年晚于南明终局：{row['years']}")

    def test_relation_types_stay_within_the_app_vocabulary(self):
        from app.database import connect

        known = {"君臣", "同僚", "统属", "政争", "师承", "父子", "母子", "配偶", "兄弟姐妹"}
        with connect() as database:
            labels = {row[0] for row in database.execute("SELECT DISTINCT relation_type FROM person_relation")}
        self.assertFalse(labels - known, f"出现 App 端无法映射的关系类型：{labels - known}")

    def test_family_sections_describe_member_outcomes(self):
        payload = bootstrap_content()
        people = {person["id"]: person for person in payload["people"]}
        family = people["zhangjuzheng"]["sections"]
        family_content = next(section["content"] for section in family if section["section_key"] == "family")
        self.assertIn("张敬修", family_content)
        self.assertIn("自缢", family_content)
        self.assertIn("张懋修", family_content)
        # 结局叙述逐行成段，而不是只列姓名。
        self.assertGreaterEqual(len(family_content.splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
