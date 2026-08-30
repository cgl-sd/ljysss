import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_person_existence.py"
SPEC = importlib.util.spec_from_file_location("audit_person_existence", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class PersonExistenceAuditTest(unittest.TestCase):
    def test_calendar_label_is_rejected_even_with_an_anchor(self):
        status, reason = AUDIT.classify(
            {"name": "九年", "title": "明代官员"},
            "九年，柳浔诸蛮复叛。",
            ["九年，柳浔诸蛮复叛。"],
            ["九年，柳浔诸蛮复叛。"],
            {178},
            in_roster=True,
        )
        self.assertEqual("rejected", status)
        self.assertIn("纪年词", reason)

    def test_ming_wiki_intro_confirms_matching_person(self):
        status, _ = AUDIT.classify(
            {"name": "海瑞", "title": "明代官员"},
            "海瑞，字汝贤，明朝官员。嘉靖年间以敢言著称。",
            [],
            [],
            set(),
            in_roster=False,
        )
        self.assertEqual("confirmed", status)

    def test_other_dynasty_intro_is_rejected(self):
        status, reason = AUDIT.classify(
            {"name": "卫青", "title": "明代官员"},
            "卫青，西汉名将，官至大将军。",
            [],
            [],
            set(),
            in_roster=True,
        )
        self.assertEqual("rejected", status)
        self.assertIn("其他朝代", reason)

    def test_wrong_same_name_wiki_page_is_rejected_even_with_mingshi_record(self):
        status, reason = AUDIT.classify(
            {"name": "张升", "title": "明代官员"},
            "张升，东汉官员。",
            [],
            ["张升，字某，明朝官员。"],
            set(),
            in_roster=True,
        )
        self.assertEqual("rejected", status)
        self.assertIn("其他朝代", reason)

    def test_mingshi_sentence_cannot_replace_a_wikipedia_intro(self):
        status, _ = AUDIT.classify(
            {"name": "孙恪", "title": "明代官员"},
            "",
            [],
            [],
            {131},
            in_roster=False,
        )
        self.assertEqual("rejected", status)

    def test_verified_imperial_title_alias_confirms(self):
        status, _ = AUDIT.classify(
            {"id": "zhuyuyu", "name": "朱聿鐭", "title": "唐王"},
            "绍武帝朱聿，为南明第三任君主。",
            [],
            [],
            set(),
            in_roster=False,
            wiki_title="绍武帝",
        )
        self.assertEqual("confirmed", status)

    def test_exact_wikipedia_title_matches_traditional_name(self):
        status, _ = AUDIT.classify(
            {"name": "庄昶", "title": "明代官员"},
            "昶，字孔旸，明朝政治人物。",
            [],
            [],
            set(),
            in_roster=False,
            wiki_title="莊昶",
        )
        self.assertEqual("confirmed", status)

    def test_disambiguation_page_is_rejected_even_when_it_lists_a_ming_person(self):
        status, reason = AUDIT.classify(
            {"name": "张温", "title": "明朝将领"},
            "历史上有数个名为张温的人：\n张温（明）：明朝初期军事将领。\n张温（东汉）：东汉人物。",
            [],
            [],
            set(),
            in_roster=False,
            wiki_title="张温",
        )
        self.assertEqual("rejected", status)
        self.assertIn("消歧页", reason)


if __name__ == "__main__":
    unittest.main()
