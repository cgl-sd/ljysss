import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_person_titles.py"
SPEC = importlib.util.spec_from_file_location("audit_person_titles", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class PersonTitleAuditTest(unittest.TestCase):
    def test_marks_generic_import_titles_for_review(self):
        self.assertTrue(AUDIT.needs_review({"name": "甲", "title": "明朝将领"}))
        self.assertTrue(AUDIT.needs_review({"name": "乙", "title": "武烈"}))
        self.assertTrue(AUDIT.needs_review({"name": "丙", "title": "明·丙"}))
        self.assertTrue(AUDIT.needs_review({"name": "丁", "title": "武烈"}))
        self.assertFalse(AUDIT.needs_review({"name": "丙", "title": "兵部尚书"}))

    def test_extracts_direct_office_or_noble_rank_from_wiki_text(self):
        person = {"name": "丁甲", "title": "明朝将领"}
        self.assertEqual(AUDIT.title_from_wiki(person, "丁甲，明朝军事将领，受封济国公。"), "济国公")

    def test_does_not_reuse_generic_identity_as_title(self):
        person = {"name": "丁甲", "title": "明朝将领"}
        self.assertEqual(AUDIT.title_from_wiki(person, "丁甲，明朝军事将领，参与多次战事。"), "")

    def test_ignores_another_persons_princely_title_without_a_subject_rank_action(self):
        person = {"name": "瞿甲", "title": "明朝将领", "category": "将帅"}
        self.assertEqual(
            AUDIT.title_from_wiki(person, "瞿甲以四川都指挥使出征。\n\n参考资料\n明朝四川都指挥使\n燕王"),
            "四川都指挥使",
        )

    def test_uses_category_label_instead_of_a_biography_sentence(self):
        person = {"name": "陈甲", "title": "明·陈甲", "category": "将帅"}
        self.assertEqual(
            AUDIT.title_from_wiki(person, "陈甲，明朝军事将领。\n\n生平\n陈甲跟随大将军出征。\n\n参考资料\n明朝都督同知"),
            "都督同知",
        )


if __name__ == "__main__":
    unittest.main()
