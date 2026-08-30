"""南明作为单一总档的基本数据约束。"""

from __future__ import annotations

import json
from pathlib import Path


CONTENT = Path(__file__).resolve().parents[1] / "data" / "content"


def rows(table: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines()]


def test_nanming_is_a_single_post_chongzhen_archive() -> None:
    reign = next(row for row in rows("reign") if row["id"] == "nanming")
    assert (reign["title"], reign["start_year"], reign["end_year"]) == ("南明", 1644, 1662)

    events = rows("event")
    south_ming_events = [event for event in events if event["reign_id"] == "nanming"]
    assert {event["id"] for event in south_ming_events} == {
        "wiki-南明", "wiki-弘光", "wiki-隆武", "wiki-扬州十日", "wiki-嘉定三屠",
    }
    assert all(reign["start_year"] <= event["year"] <= reign["end_year"] for event in south_ming_events)
    assert not [event for event in events if event["reign_id"] == "chongzhen" and event["year"] > 1644]


def test_nanming_people_have_a_source_backed_archive_year() -> None:
    people = [person for person in rows("person") if "南明" in person["reign"].split("、")]
    assert len(people) >= 20
    assert all(1644 <= person.get("archive_start_year", 0) <= 1662 for person in people)
    assert {person["name"] for person in people} >= {"朱由崧", "朱由榔", "史可法", "郑成功"}
