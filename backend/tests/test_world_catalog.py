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
        self.assertEqual(
            {"中枢政务", "监察司法", "军事卫所", "内廷宦官", "地方治理", "教育与专门"},
            categories,
        )
        self.assertTrue(
            {"国子监", "翰林院", "钦天监", "太医院", "京军三大营", "府州县学", "詹事府", "太常寺", "府、州、县与地方衙门", "土司与西南边地治理"}
            <= {row["name"] for row in institutions}
        )
        self.assertEqual({"制度", "器物", "宫陵"}, {row["category"] for row in specials})
        self.assertFalse(any(row["id"].startswith("wiki-") for row in specials))

    def test_every_institution_has_four_readable_detail_sections(self):
        institutions = load_rows("institution")
        sections = load_rows("institution_section")
        sources = {row["id"] for row in load_rows("source")}
        grouped = {}
        for section in sections:
            grouped.setdefault(section["institution_id"], []).append(section)
            self.assertIn(section["source_id"], sources)
            self.assertGreaterEqual(len(section["content"].strip()), 50)

        self.assertEqual({row["id"] for row in institutions}, set(grouped))
        for institution_id, rows in grouped.items():
            self.assertEqual(
                ["duty", "structure", "operation", "evolution"],
                [row["section_key"] for row in sorted(rows, key=lambda row: row["position"])],
                institution_id,
            )

    def test_institution_people_only_link_to_published_people(self):
        people = {row["id"] for row in load_rows("person")}
        institutions = {row["id"] for row in load_rows("institution")}
        sources = {row["id"] for row in load_rows("source")}
        for row in load_rows("institution_person"):
            self.assertIn(row["institution_id"], institutions)
            self.assertIn(row["person_id"], people)
            self.assertIn(row["source_id"], sources)
            self.assertTrue(row["role"].strip())

    def test_cabinet_promotion_guide_has_separate_routes(self):
        rows = [row for row in load_rows("institution_promotion") if row["institution_id"] == "grand-secretariat"]
        tracks = {row.get("track") for row in rows}
        self.assertEqual({"科举翰林线", "部院、地方转入线", "特简入阁"}, tracks)
        self.assertEqual(len(rows), len({row["position"] for row in rows}))

    def test_every_special_has_readable_sections_and_valid_person_links(self):
        specials = {row["id"] for row in load_rows("special_item")}
        people = {row["id"] for row in load_rows("person")}
        sources = {row["id"] for row in load_rows("source")}
        sections_by_item = {}
        for section in load_rows("special_section"):
            self.assertIn(section["special_item_id"], specials)
            self.assertIn(section["source_id"], sources)
            self.assertGreaterEqual(len(section["content"].strip()), 50)
            sections_by_item.setdefault(section["special_item_id"], []).append(section)
        self.assertEqual(specials, set(sections_by_item))
        for item_id, rows in sections_by_item.items():
            self.assertEqual(
                ["meaning", "form", "practice", "legacy"],
                [row["section_key"] for row in sorted(rows, key=lambda row: row["position"])],
                item_id,
            )
        for row in load_rows("special_person"):
            self.assertIn(row["special_item_id"], specials)
            self.assertIn(row["person_id"], people)
            self.assertIn(row["source_id"], sources)

    def test_world_details_register_reading_and_special_image_rights(self):
        institutions = {row["id"] for row in load_rows("institution")}
        specials = {row["id"] for row in load_rows("special_item")}
        references = load_rows("content_reference")
        institution_readings = {
            row["content_id"]
            for row in references
            if row["content_type"] == "institution" and row["section_key"] == "reading"
        }
        special_readings = {
            row["content_id"]
            for row in references
            if row["content_type"] == "special" and row["section_key"] == "reading"
        }
        special_images = [
            row for row in references
            if row["content_type"] == "special" and row["section_key"] == "image"
        ]
        self.assertEqual(institutions, institution_readings)
        self.assertEqual(specials, special_readings)
        self.assertEqual(specials, {row["content_id"] for row in special_images})
        self.assertTrue(all("许可" in row["note"] for row in special_images))
        readings = [
            row for row in references
            if row["section_key"] == "reading" and row["content_type"] in {"institution", "special"}
        ]
        self.assertTrue(all(row["url"].startswith("https://") for row in readings))
        self.assertFalse(any("相关志与本纪" in row["title"] for row in readings))
