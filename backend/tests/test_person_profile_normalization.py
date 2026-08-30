import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "normalize_person_profiles.py"
SPEC = importlib.util.spec_from_file_location("normalize_person_profiles", SCRIPT)
assert SPEC and SPEC.loader
NORMALIZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NORMALIZE)


class PersonProfileNormalizationTest(unittest.TestCase):
    def test_removes_empty_parentheses_reference_tail_and_category_short_lines(self):
        source = """张甲（），字子明，明朝政治人物。

生平

早年
张甲早年读书，后登进士。

参考文献

明朝吏部官员"""
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertIn("张甲，字子明，明朝政治人物。", result)
        self.assertIn("早年", result)
        self.assertNotIn("（）", result)
        self.assertNotIn("参考文献", result)
        self.assertNotIn("明朝吏部官员", result)

    def test_long_unheaded_biography_uses_generic_non_conflicting_inner_headings(self):
        source = "".join(f"第{i}件事发生于明朝，人物因此受到重用。" for i in range(1, 80))
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertIn("概览", result)
        self.assertIn("纪事", result)
        self.assertNotIn("生平经历", result)

    def test_existing_source_heading_is_kept_without_generating_generic_headings(self):
        source = "早年\n人物自幼好学，后来入仕。\n晚年\n人物归乡著述。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertIn("早年", result)
        self.assertIn("晚年", result)
        self.assertNotIn("概览", result)
        self.assertNotIn("纪事", result)

    def test_non_biographical_sections_are_removed_with_their_body(self):
        source = "生平\n人物早年入仕。\n著作\n《甲书》与《乙书》。\n评价\n后世称许。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertIn("人物早年入仕。", result)
        self.assertNotIn("著作", result)
        self.assertNotIn("甲书", result)
        self.assertNotIn("评价", result)

    def test_reference_and_family_subsections_are_not_kept_as_life_content(self):
        source = "人物入仕有政绩。\n兄弟\n甲、乙。\n年号\n干定。\n参考书目\n《明史》。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertEqual(result, "人物入仕有政绩。")

    def test_life_after_a_family_subsection_is_still_kept(self):
        source = "人物概况。\n家族\n父亲甲。\n生平\n人物后来入仕并卒于任内。\n参考资料\n《明史》。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertEqual(result, "人物概况。\n\n人物后来入仕并卒于任内。")

    def test_short_category_line_is_not_misread_as_a_subheading(self):
        source = "人物以诗文闻名。\n明朝诗人\nY"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertEqual(result, "人物以诗文闻名。")

    def test_direct_ming_military_description_beats_noble_title(self):
        person = {"category": "封爵", "title": "魏国公"}
        source = "徐达，字天德。徐达是明朝开国功臣、军事将领。"
        self.assertEqual(NORMALIZE.inferred_category(person, source), "将帅")

    def test_mentioning_an_emperor_does_not_turn_subject_into_emperor(self):
        person = {"category": "将帅", "title": "荣定"}
        source = "梅殷是中国明朝开国君主朱元璋的女婿，曾参与军事事务。"
        self.assertEqual(NORMALIZE.inferred_category(person, source), "将帅")


if __name__ == "__main__":
    unittest.main()
