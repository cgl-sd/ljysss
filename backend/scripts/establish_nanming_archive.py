#!/usr/bin/env python3
"""Establish the single 南明 archive in the editorial JSONL catalog.

南明不是单一帝号，故不拆成弘光、隆武、绍武、永历等二级“朝”。人物的
``archive_start_year`` 表示其首次进入南明政治／军事舞台的年份，只用于南明
档案的时间排序；人物原有年号资料仍完整保留在 ``reign`` 字段中。
"""

from __future__ import annotations

import json
from pathlib import Path


CONTENT = Path(__file__).resolve().parent.parent / "data" / "content"

NANMING_PEOPLE = {
    # 南明诸主与监国
    "zhuyousong": 1644,
    "zhuyihai": 1645,
    "zhuyujian": 1645,
    "zhuyuyu": 1646,
    "zhuyoulang": 1646,
    # 弘光、隆武、鲁监国、永历诸政权中有明确任事或统兵记录者
    "shikefa": 1644,
    "liuzeqing": 1644,
    "gaojie": 1644,
    "huangdegong": 1644,
    "mashiying": 1644,
    "gaohongtu": 1644,
    "chenzizhuang": 1644,
    "qiansule": 1644,
    "zhangguowei": 1644,
    "hewuzou": 1644,
    "zhengchenggong": 1645,
    "zhengzhilong": 1645,
    "zhanghuangyan": 1645,
    "zhangmingzhen": 1645,
    "qushisi": 1645,
    "huangdaozhou": 1645,
    # 嘉定抗清事件的直接参与者
    "houdongceng": 1645,
    "huangchunyao": 1645,
}

EVENT_UPDATES = {
    "wiki-南明": {
        "year": 1644,
        "title": "南明诸政权形成",
        "summary": "北京失守后，明朝宗室与遗臣在南方相继建立弘光、鲁监国、隆武、绍武与永历等政权。",
        "detail": "1644年北京失守、崇祯帝殉国后，南京与南方各地仍保有明朝官署和军政力量。福王朱由崧在南京即位，揭开南明诸政权并行的时期；其后鲁王朱以海监国、唐王朱聿键称帝、桂王朱由榔即位。各政权虽同奉明室，却并非彼此隶属，抵抗与内部分合交织，延续至1662年永历帝遇害。",
        "participants": "朱由崧、朱以海、朱聿键、朱由榔",
    },
    "wiki-弘光": {
        "year": 1644,
        "title": "弘光政权建立",
        "summary": "福王朱由崧在南京即位，次年改元弘光，南明弘光政权由此形成。",
        "detail": "1644年五月，福王朱由崧在南京先称监国，继而即皇帝位，次年改元弘光。南京朝廷以恢复明室为名组织江南军政，但很快面临清军南下与内部权力竞争；1645年南京失守，弘光政权覆亡。",
        "participants": "朱由崧、马士英、高弘图、史可法",
    },
    "wiki-隆武": {
        "year": 1645,
        "title": "隆武政权建立",
        "summary": "唐王朱聿键在福州即位，改元隆武，形成南明另一支主要政权。",
        "detail": "1645年弘光政权覆亡后，唐王朱聿键在郑芝龙等人拥立下于福州即位，次年改元隆武。隆武朝廷尝试整合福建与东南抗清力量，但与鲁王监国等政权并行，未能形成统一指挥。",
        "participants": "朱聿键、郑芝龙、郑成功",
    },
    "wiki-扬州十日": {},
    "wiki-嘉定三屠": {"participants": "侯峒曾、黄淳耀"},
}


def read_rows(table: str) -> list[dict]:
    path = CONTENT / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(table: str, rows: list[dict]) -> None:
    path = CONTENT / f"{table}.jsonl"
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    reigns = read_rows("reign")
    reign_by_id = {row["id"]: row for row in reigns}
    reign_by_id["nanming"] = {
        "id": "nanming",
        "title": "南明",
        "start_year": 1644,
        "end_year": 1662,
        "summary": "北京失守后，明朝宗室与遗臣在南方相继建立多个政权；本档按时间统览其人事与大事。",
    }
    write_rows("reign", sorted(reign_by_id.values(), key=lambda row: (row["start_year"], row["id"])))

    people = read_rows("person")
    found_people = set()
    for person in people:
        start_year = NANMING_PEOPLE.get(person["id"])
        if start_year is None:
            continue
        found_people.add(person["id"])
        reigns_text = [part for part in person["reign"].split("、") if part]
        if "南明" not in reigns_text:
            reigns_text.append("南明")
        person["reign"] = "、".join(reigns_text)
        person["archive_start_year"] = start_year
    missing = sorted(set(NANMING_PEOPLE) - found_people)
    if missing:
        raise RuntimeError(f"South Ming people missing from catalog: {', '.join(missing)}")
    write_rows("person", people)

    events = read_rows("event")
    event_by_id = {event["id"]: event for event in events}
    missing_events = sorted(set(EVENT_UPDATES) - set(event_by_id))
    if missing_events:
        raise RuntimeError(f"South Ming events missing from catalog: {', '.join(missing_events)}")
    for event_id, fields in EVENT_UPDATES.items():
        event_by_id[event_id]["reign_id"] = "nanming"
        event_by_id[event_id].update(fields)
    write_rows("event", events)

    participant_rows = read_rows("event_participant")
    existing = {(row["event_id"], row["person_id"]) for row in participant_rows}
    for event_id, person_id in (
        ("wiki-嘉定三屠", "houdongceng"),
        ("wiki-嘉定三屠", "huangchunyao"),
    ):
        if (event_id, person_id) not in existing:
            participant_rows.append({"event_id": event_id, "person_id": person_id, "role": "参与"})
    write_rows("event_participant", participant_rows)


if __name__ == "__main__":
    main()
