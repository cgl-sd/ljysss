import json
from pathlib import Path
import unittest


CONTENT = Path(__file__).resolve().parents[1] / "data" / "content"


def load_rows(table: str):
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


class TravelGuideCatalogTests(unittest.TestCase):
    def test_every_guide_has_a_unique_asset_and_readable_sections(self):
        guides = load_rows("travel_guide")
        sections = load_rows("travel_guide_section")
        sources = {row["id"] for row in load_rows("source")}
        self.assertEqual(10, len(guides))
        self.assertEqual(len(guides), len({row["id"] for row in guides}))
        self.assertEqual(len(guides), len({row["image_asset"] for row in guides}))
        self.assertTrue(all(row["source_id"] in sources for row in guides))
        by_guide = {}
        for section in sections:
            self.assertIn(section["source_id"], sources)
            self.assertGreaterEqual(len(section["content"].strip()), 50)
            by_guide.setdefault(section["travel_guide_id"], []).append(section)
        self.assertEqual({row["id"] for row in guides}, set(by_guide))
        self.assertTrue(all(len(rows) >= 2 for rows in by_guide.values()))
        self.assertTrue(all(len(rows) == len({row["section_key"] for row in rows}) for rows in by_guide.values()))

    def test_high_risk_entry_does_not_contain_weapon_instructions(self):
        metal = next(row for row in load_rows("travel_guide") if row["id"] == "guide-metallurgy-safety")
        sections = [row["content"] for row in load_rows("travel_guide_section") if row["travel_guide_id"] == metal["id"]]
        self.assertIn("危险器材不得私自处理", metal["description"])
        self.assertTrue(any("绝不提供火器" in content for content in sections))

    def test_every_guide_uses_a_documented_subject_source(self):
        guides = load_rows("travel_guide")
        sources = {row["id"]: row for row in load_rows("source")}
        self.assertTrue(all(row["source_id"] in sources for row in guides))
        self.assertTrue(all(sources[row["source_id"]]["url"] for row in guides))
        self.assertNotIn("guide-safety-editorial-v1", {row["source_id"] for row in guides})
