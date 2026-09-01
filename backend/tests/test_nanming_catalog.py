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
    assert len(south_ming_events) > 0
    # 南明作为一个总档，事件按实际起始年份排列；明郑及夔东遗绪可延续至1664。
    assert all(reign["start_year"] <= event["year"] <= 1664 for event in south_ming_events)
    assert not [event for event in events if event["reign_id"] == "chongzhen" and event["year"] > 1644]


def test_nanming_people_have_a_source_backed_archive_year() -> None:
    people = [person for person in rows("person") if "南明" in person["reign"].split("、")]
    assert len(people) >= 20
    assert all(1644 <= person.get("archive_start_year", 0) <= 1662 for person in people)
    assert {person["name"] for person in people} >= {"朱由崧", "朱由榔", "史可法", "郑成功"}


def test_events_are_assigned_to_their_reign_and_month_labels_are_readable() -> None:
    reigns = {row["id"]: row for row in rows("reign")}
    events = rows("event")
    for event in events:
        reign = reigns[event["reign_id"]]
        if event["reign_id"] == "nanming":
            assert event["year"] >= 1644
        elif event["reign_id"] == "hongwu":
            # 开国连续战事从 1367 年开始，作为洪武档案的前置事件保留。
            assert 1367 <= event["year"] <= reign["end_year"]
        else:
            assert reign["start_year"] <= event["year"] <= reign["end_year"]
        assert event["month"] == "全年" or event["month"].endswith("月")
