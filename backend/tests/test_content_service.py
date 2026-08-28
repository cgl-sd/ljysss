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
        self.assertGreaterEqual(len(payload["people"]), 130)
        self.assertGreaterEqual(len(payload["relationships"]), 49)
        self.assertGreaterEqual(len(payload["institutions"]), 12)

    def test_person_detail_exposes_source_status_and_relationships(self):
        person = get_person("zhangjuzheng")
        self.assertEqual("张居正", person["name"])
        self.assertTrue(person["review_status"])
        self.assertTrue(person["relationships"])


if __name__ == "__main__":
    unittest.main()
