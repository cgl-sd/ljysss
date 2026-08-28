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
        self.assertGreaterEqual(len(payload["people"]), 800)
        self.assertGreaterEqual(len(payload["relationships"]), 63)
        self.assertGreaterEqual(len(payload["institutions"]), 12)

    def test_bootstrap_people_expose_structured_sections(self):
        payload = bootstrap_content()
        person = next(item for item in payload["people"] if item["id"] == "zhangjuzheng")
        self.assertIn("sections", person)

    def test_rebuild_schema_exposes_uniform_section_endpoints(self):
        from app.main import get_event_sections

        sections = {section["section_key"] for section in get_event_sections("hongwu-founding")}
        self.assertEqual({"background", "course", "people", "result", "impact", "verification"}, sections)

    def test_every_person_and_event_has_a_uniform_profile_template(self):
        from app.database import connect

        with connect() as database:
            people = database.execute("SELECT COUNT(*) FROM person").fetchone()[0]
            events = database.execute("SELECT COUNT(*) FROM event").fetchone()[0]
            events_with_background = database.execute(
                "SELECT COUNT(DISTINCT event_id) FROM event_section WHERE section_key = 'background'"
            ).fetchone()[0]
        self.assertGreaterEqual(people, 800)
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
        self.assertEqual({"徐辉祖", "徐添福", "徐膺绪", "徐增寿"}, children)

    def test_famous_people_are_present_in_catalog(self):
        payload = bootstrap_content()
        names = {person["name"] for person in payload["people"]}
        expected = {
            "朱元璋", "张居正", "海瑞", "戚继光", "郑和", "王守仁",
            "李时珍", "马皇后", "朱权", "朱载堉",
        }
        self.assertTrue(expected <= names)

    def test_new_categories_include_consorts_and_princes(self):
        payload = bootstrap_content()
        categories = {person["category"] for person in payload["people"]}
        self.assertIn("后妃", categories)
        self.assertIn("藩王", categories)


if __name__ == "__main__":
    unittest.main()
