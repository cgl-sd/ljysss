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

        sections = {section["section_key"] for section in get_event_sections("hongwu-founding")}
        self.assertEqual({"background", "course", "people", "result", "impact", "verification"}, sections)

    def test_every_person_and_event_has_a_uniform_profile_template(self):
        from app.database import connect

        with connect() as database:
            people = database.execute("SELECT COUNT(*) FROM person").fetchone()[0]
            people_with_life = database.execute(
                "SELECT COUNT(DISTINCT person_id) FROM person_section WHERE section_key = 'life'"
            ).fetchone()[0]
            events = database.execute("SELECT COUNT(*) FROM event").fetchone()[0]
            events_with_background = database.execute(
                "SELECT COUNT(DISTINCT event_id) FROM event_section WHERE section_key = 'background'"
            ).fetchone()[0]
        self.assertEqual(people, people_with_life)
        self.assertEqual(events, events_with_background)

    def test_person_research_audit_is_private_and_uses_recoverable_states(self):
        from app.database import connect

        with connect() as database:
            statuses = {
                row[0]
                for row in database.execute(
                    "SELECT DISTINCT status FROM person_research WHERE provider = 'wikidata'"
                )
            }
        self.assertTrue(statuses)
        self.assertTrue(statuses <= {"matched", "not_found", "identity_rejected", "network_failed"})

    def test_researched_person_profile_survives_catalog_synchronization(self):
        person = get_person("caobianjiao")
        sections = {section["section_key"]: section["content"] for section in person["sections"]}
        self.assertEqual("已校验", person["verification_status"])
        self.assertIn("公开资料记录的生卒信息", sections["life"])
        self.assertIn("family", sections)

    def test_baike_verified_profiles_include_education_and_children(self):
        person = get_person("zhangjuzheng")
        self.assertIn("嘉靖二十六年（1547）中进士", person["biography"])
        self.assertIn("张允修", person["family_summary"])
        self.assertEqual("已校验", person["verification_status"])

    def test_same_name_entity_is_not_mixed_into_the_wrong_profile(self):
        person = get_person("wangzhi-minister")
        self.assertEqual("未校验", person["verification_status"])
        self.assertNotIn("海盗", person["biography"])

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

    def test_cbdb_api_enriched_profile_has_factual_life_and_family_sections(self):
        person = get_person("cbdb-100539")
        self.assertIn("義烏", person["biography"])
        self.assertIn("父亲：方汝霖", person["family_summary"])
        self.assertEqual("已校验", person["verification_status"])

    def test_every_imported_person_has_a_completed_cbdb_api_outcome(self):
        from app.database import connect

        with connect() as database:
            imported = database.execute(
                "SELECT COUNT(*) FROM person WHERE source_id = 'cbdb-20210525'"
            ).fetchone()[0]
            completed = database.execute(
                """
                SELECT COUNT(*) FROM person
                WHERE source_id = 'cbdb-20210525'
                  AND EXISTS (
                      SELECT 1 FROM person_research AS research
                      WHERE research.person_id = person.id
                        AND research.provider = 'cbdb_api'
                        AND research.status IN ('matched', 'not_found')
                  )
                """
            ).fetchone()[0]
        self.assertEqual(imported, completed)


if __name__ == "__main__":
    unittest.main()
