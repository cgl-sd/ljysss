#!/usr/bin/env python3
"""把子代理写好的手册扩充正文合并进 travel_guide_section.jsonl。

输入：一个或多个 JSON 文件（每条 {"id": "...", "sections": [{"key": "...", "content": "..."}]}），
可传多个文件合并；也可直接传单个含多条的文件。缺省从 ./guide_expansions/*.json 读取。
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]  # backend/
SECTION_PATH = BASE / "data/content/travel_guide_section.jsonl"


def load_inputs(paths):
    rows = []
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows.extend(data)
        else:
            rows.append(data)
    return rows


def main() -> None:
    paths = sys.argv[1:] or sorted(str(p) for p in Path("guide_expansions").glob("*.json"))
    rows = load_inputs(paths)
    sections = [json.loads(line) for line in SECTION_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_key = {(s["travel_guide_id"], s["section_key"]): s for s in sections}

    applied = 0
    for entry in rows:
        gid = entry["id"]
        for sec in entry["sections"]:
            key = sec["key"]
            content = sec["content"].strip()
            target = by_key.get((gid, key))
            if target is None:
                raise SystemExit(f"no such section: {gid}/{key}")
            if len(content) < 1500:
                raise SystemExit(f"too short ({len(content)}): {gid}/{key}")
            target["content"] = content
            applied += 1

    SECTION_PATH.write_text(
        "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in sections),
        encoding="utf-8",
    )
    print(f"applied {applied} sections")
    for s in sections:
        if s["travel_guide_id"].startswith("guide-"):
            print(f"  {s['travel_guide_id']}/{s['section_key']}: {len(s['content'])}字")


if __name__ == "__main__":
    main()
