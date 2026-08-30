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

    def test_media_nested_headings_and_family_lists_do_not_reopen_life(self):
        source = "人物在任时整饬政务。\n影视形象\n电视剧\n某剧由演员饰演。\n家庭成员\n子\n甲。\n女\n乙。\n参考资料\n《明史》。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertEqual(result, "人物在任时整饬政务。")

    def test_embedded_family_and_works_sentences_are_removed_semantically(self):
        source = "人物是某帝第三子。人物早年入仕。其父为某官。著有《甲集》。后因政绩升任尚书。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertEqual(result, "人物早年入仕。\n\n后因政绩升任尚书。")

    def test_crown_prince_accession_is_not_mistaken_for_family_succession(self):
        result = NORMALIZE.clean_wikipedia_bio("皇帝去世后，太子嗣位，改元建文。")
        self.assertEqual(result, "皇帝去世后，太子嗣位，改元建文。")

    def test_genealogical_list_is_removed_even_without_a_family_heading(self):
        result = NORMALIZE.clean_wikipedia_bio("人物曾祖父甲、祖父乙、父亲丙，家族世代务农。人物后来从军立功。")
        self.assertEqual(result, "人物后来从军立功。")

    def test_in_law_title_is_treated_as_family_information(self):
        result = NORMALIZE.clean_wikipedia_bio("人物同时也是皇帝的国丈。人物随后出征北方。")
        self.assertEqual(result, "人物随后出征北方。")

    def test_family_clause_is_removed_without_losing_same_sentence_biography(self):
        result = NORMALIZE.clean_wikipedia_bio("人物，某帝第三子，后继王位并镇守边地。")
        self.assertEqual(result, "人物，后继王位并镇守边地。")

    def test_category_fragment_left_after_family_removal_is_not_shown(self):
        result = NORMALIZE.clean_wikipedia_bio("人物，明朝政治人物，某官之弟。后任知县。")
        self.assertEqual(result, "人物\n\n后任知县。")

    def test_long_non_narrative_section_label_starts_a_skip_section(self):
        source = "人物从政有绩。\n关于人物生母争议中\n这段材料不应展示。\n参考资料\n《明史》。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertEqual(result, "人物从政有绩。")

    def test_modern_life_text_is_converted_to_simplified_chinese(self):
        source = "人物為明朝官員，歷任禮部尚書。\n早年\n其後參與政務。"
        result = NORMALIZE.clean_wikipedia_bio(source)
        self.assertIn("人物为明朝官员", result)
        self.assertIn("其后参与政务", result)
        self.assertNotIn("為", result)

    def test_simplification_preserves_the_qianqing_palace_proper_noun(self):
        result = NORMALIZE.clean_wikipedia_bio("人物上疏乾清宫火灾，歷陳政事。")
        self.assertIn("乾清宫", result)
        self.assertIn("历陈政事", result)

    def test_inline_evaluation_is_removed_but_identity_is_kept(self):
        result = NORMALIZE.clean_wikipedia_bio("人物，明代书法家，被皇帝誉为“第一人”。1403年入朝任职。")
        self.assertEqual(result, "人物，明代书法家。\n\n1403年入朝任职。")

    def test_parenthesized_see_also_line_is_not_shown_in_life(self):
        result = NORMALIZE.clean_wikipedia_bio("人物生平（参看人物墓）。\n（参看人物墓）")
        self.assertEqual(result, "人物生平。")

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
