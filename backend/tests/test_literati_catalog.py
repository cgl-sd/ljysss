import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "finalize_people_catalog.py"
SPEC = importlib.util.spec_from_file_location("finalize_people_catalog", SCRIPT)
assert SPEC and SPEC.loader
CATALOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CATALOG)


class LiteratiCatalogTest(unittest.TestCase):
    def test_literati_official_overrides_use_verified_offices_and_move_to_ministers(self):
        person = {"id": "lixiyan", "name": "李希颜", "title": "高皇后", "category": "文苑"}
        self.assertEqual(CATALOG.canonical_title(person, ""), "左春坊右赞善")
        self.assertEqual(CATALOG.corrected_category(person, "", "左春坊右赞善", "文苑"), "朝臣")

    def test_literati_validator_rejects_exam_and_family_labels(self):
        issues = CATALOG.validate_literati([
            {"id": "wrong", "category": "文苑", "title": "二十六岁中举人"},
            {"id": "wangzhenqing", "category": "文苑", "title": "诗人"},
        ])
        self.assertTrue(any("wrong" in issue for issue in issues))
        self.assertFalse(any("wangzhenqing" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
