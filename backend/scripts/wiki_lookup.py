#!/usr/bin/env python3
"""从本地中文维基 parquet 快照按标题批量提取条目正文，用于手册写作核实。"""
import pyarrow.compute as pc
import pyarrow.parquet as pq
import glob
import sys

FILES = sorted(glob.glob("backend/sources/wikipedia_zh/train-*.parquet"))


def find(title: str, limit: int = 1):
    hits = []
    for f in FILES:
        pf = pq.ParquetFile(f)
        t = pf.read(columns=["title", "text"])
        mask = pc.equal(pc.field("title"), title)
        sel = t.filter(mask)
        if sel.num_rows:
            hits.extend(sel.column("text").to_pylist())
            if len(hits) >= limit:
                break
    return hits


def fuzzy(keyword: str, limit: int = 3):
    """按标题包含关键字搜索（大小写不敏感）。"""
    hits = []
    for f in FILES:
        pf = pq.ParquetFile(f)
        t = pf.read(columns=["title", "text"])
        mask = pc.match_substring(pc.field("title"), keyword)
        sel = t.filter(mask)
        for row in sel.to_pylist():
            hits.append((row["title"], row["text"]))
        if len(hits) >= limit:
            break
    return hits


if __name__ == "__main__":
    for kw in sys.argv[1:]:
        print("=" * 20, kw, "=" * 20)
        for title, text in fuzzy(kw):
            print(f"--- {title} ---")
            print(text[:900].replace("\n", " "))
            print()
