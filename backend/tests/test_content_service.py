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
        self.assertGreaterEqual(len(payload["people"]), 1_100)
        self.assertGreaterEqual(len(payload["relationships"]), 63)
        self.assertGreaterEqual(len(payload["institutions"]), 12)

    def test_person_detail_exposes_source_status_and_relationships(self):
        person = get_person("zhangjuzheng")
        self.assertEqual("张居正", person["name"])
        self.assertTrue(person["review_status"])
        self.assertTrue(person["relationships"])
        self.assertIn("sections", person)

    def test_rebuild_schema_exposes_uniform_section_endpoints(self):
        from app.main import get_event_sections

        self.assertEqual([], get_event_sections("hongwu-founding"))

    def test_noble_family_children_are_structured_relationships(self):
        person = get_person("xuda")
        children = {
            relationship["to_name"]
            for relationship in person["relationships"]
            if relationship["from_name"] == "徐达" and relationship["relation_type"] == "父子"
        }
        self.assertEqual({"徐辉祖", "徐添福", "徐膺绪", "徐增寿"}, children)

    def test_cbdb_import_keeps_its_own_provenance(self):
        payload = bootstrap_content()
        imported = [person for person in payload["people"] if person["source_id"] == "cbdb-20210525"]
        self.assertGreaterEqual(len(imported), 1_000)
        self.assertTrue(all(person["review_status"] for person in imported))


if __name__ == "__main__":
    unittest.main()
