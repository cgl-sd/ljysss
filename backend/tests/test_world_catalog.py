import json
from pathlib import Path
import unittest


CONTENT = Path(__file__).resolve().parents[1] / "data" / "content"


def load_rows(table: str):
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


class WorldCatalogTests(unittest.TestCase):
    def test_institution_and_special_catalogs_do_not_publish_same_subject(self):
        institutions = load_rows("institution")
        specials = load_rows("special_item")
        institution_names = {row["name"] for row in institutions}
        special_names = {row["name"] for row in specials}
        self.assertFalse(institution_names & special_names)

    def test_world_catalog_keeps_formal_institutions_and_curated_specials(self):
        institutions = load_rows("institution")
        specials = load_rows("special_item")
        categories = {row["category"] for row in institutions}
        self.assertTrue({"中央政务", "监察司法", "军事卫所", "内廷宦官", "地方治理", "教育礼制"} <= categories)
        self.assertTrue({"国子监", "翰林院", "钦天监", "太医院"} <= {row["name"] for row in institutions})
        self.assertEqual({"制度", "器物", "宫阙", "陵寝"}, {row["category"] for row in specials})
        self.assertFalse(any(row["id"].startswith("wiki-") for row in specials))
