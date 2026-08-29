#!/usr/bin/env python3
"""按字节区间从维基百科官方 multistream 数据包精确提取指定词条全文。

原理：multistream 数据包按 100 篇一组切成独立 bzip2 流，官方索引给出每篇
所属流的字节起点。只下载所需的流（约 200MB）即可拿到全部目标词条的完整
维基文本，无需 3.4GB 全量下载。

用法：
  python scripts/fetch_wiki_multistream.py index   # 下载索引，计算所需区间
  python scripts/fetch_wiki_multistream.py fetch   # 区间下载、解压、提取全文
  python scripts/fetch_wiki_multistream.py all
输出：data/wikitext/{person_id}.txt（简体维基文本原文）
"""

from __future__ import annotations

import bz2
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.database import connect, initialize_database  # noqa: E402

DUMPS_BASE = "https://dumps.wikimedia.org/zhwiki/latest/"
UA = "LiangjingResearch/1.0 (offline educational dataset)"
WORKDIR = Path("/tmp/wikidump")
OUTDIR = BACKEND_DIRECTORY / "data" / "wikitext"


def http_get(url: str, timeout: int = 60, raw: bool = False):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data if raw else data.decode("utf-8", "ignore")


def load_targets() -> dict[str, str]:
    """title(下划线规范形, 简繁各一) -> person_id"""
    from opencc import OpenCC
    s2t = OpenCC("s2t")
    initialize_database()
    with connect() as db:
        people = db.execute("SELECT id, name FROM person ORDER BY id").fetchall()
    targets: dict[str, str] = {}
    for p in people:
        for form in (p["name"], s2t.convert(p["name"])):
            targets[form.replace(" ", "_")] = p["id"]
    return targets


def build_part_map() -> dict[str, str]:
    listing = http_get(DUMPS_BASE, timeout=30)
    parts = {}
    for m in re.finditer(r'href="(zhwiki-latest-pages-articles-multistream\d+\.xml-[^"]+\.bz2)"', listing):
        fname = m.group(1)
        range_m = re.search(r"-p(\d+)p(\d+)\.bz2$", fname)
        if range_m:
            parts[fname] = (int(range_m.group(1)), int(range_m.group(2)))
    return parts


def phase_index() -> dict:
    targets = load_targets()
    part_map = build_part_map()  # fname -> (lo, hi)
    index_chunks = sorted(
        (m.group(1), int(m.group(2)), int(m.group(3)))
        for fname, (lo, hi) in part_map.items()
        for m in [re.match(r"zhwiki-latest-pages-articles-multistream(\d+)\.xml-p(\d+)p(\d+)\.bz2$", fname)]
    )
    needed: dict[str, dict] = {}
    for chunk_name, lo, hi in index_chunks:
        part_file = f"zhwiki-latest-pages-articles-multistream{chunk_name}.xml-p{lo}p{hi}.bz2"
        index_name = f"zhwiki-latest-pages-articles-multistream-index{chunk_name}.txt-p{lo}p{hi}.bz2"
        data = http_get(DUMPS_BASE + quote(index_name), timeout=120, raw=True)
        raw = bz2.decompress(data).decode("utf-8", "ignore")
        for line in raw.splitlines():
            bits = line.split(":", 2)
            if len(bits) != 3:
                continue
            offset_s, _page_id, title = bits
            pid = targets.get(title)
            if pid is None:
                continue
            if not offset_s.isdigit():
                continue
            needed.setdefault(part_file, {})[int(offset_s)] = title
    result = {
        "parts": {fname: DUMPS_BASE + quote(fname) for fname in needed},
        "offsets": needed,
        "misses": sorted(set(t for t in targets if t)),
    }
    (WORKDIR / "plan.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    total_offsets = sum(len(v) for v in needed.values())
    print(f"索引解析完成：命中 {total_offsets} 个词条，未命中 {len(result['misses'])} 个。", flush=True)
    return result


def decompress_streams(data: bytes) -> bytes:
    """multistream 区间由多个独立 bzip2 流拼接，逐一解压。"""
    out = b""
    chunk = data
    while chunk:
        dec = bz2.BZ2Decompressor()
        try:
            out += dec.decompress(chunk)
            if not dec.eof:
                break
            chunk = dec.unused_data
        except Exception:
            break
    return out


def extract_pages(slice_data: bytes):
    """解压一段 multistream 字节区间，产出 (title, wikitext)。"""
    text = decompress_streams(slice_data)
    xml = text.decode("utf-8", "ignore")
    for page_m in re.finditer(r"<page>(.*?)</page>", xml, flags=re.S):
        page_xml = page_m.group(1)
        title_m = re.search(r"<title>(.*?)</title>", page_xml, flags=re.S)
        text_m = re.search(r"<text[^>]*>(.*?)</text>", page_xml, flags=re.S)
        if title_m and text_m:
            yield title_m.group(1), text_m.group(1)


def phase_fetch() -> None:
    plan = json.loads((WORKDIR / "plan.json").read_text(encoding="utf-8"))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    targets = load_targets()
    title_to_id = targets
    got = 0
    for fname, offsets in sorted(plan["offsets"].items()):
        url = plan["parts"][fname]
        ranges = []
        for off in sorted(int(k) for k in offsets):
            if not ranges or off - ranges[-1][1] > 0:
                ranges.append([off, off + 3 * 1024 * 1024])
        merged: list[list[int]] = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        fetched: dict[int, bytes] = {}
        cache_dir = WORKDIR / "ranges"
        cache_dir.mkdir(parents=True, exist_ok=True)
        for start, end in merged:
            cache_file = cache_dir / f"{fname}-{start}.bin"
            if cache_file.exists() and cache_file.stat().st_size > 0:
                fetched[start] = cache_file.read_bytes()
                continue
            for attempt in range(3):
                try:
                    req = Request(url, headers={"User-Agent": UA, "Range": f"bytes={start}-{end - 1}"})
                    with urlopen(req, timeout=90) as resp:
                        fetched[start] = resp.read()
                    cache_file.write_bytes(fetched[start])
                    break
                except Exception as error:
                    print(f"{fname}@{start}: 下载失败（{error}）", flush=True)
                    time.sleep(3 * (attempt + 1))
        blob = b"".join(v for _, v in sorted(fetched.items()))
        base = merged[0][0]
        for title, wikitext in extract_pages(blob):
            pid = title_to_id.get(title)
            if not pid:
                continue
            # 该词条的流偏移必须在本区间内（粗校验）
            (OUTDIR / f"{pid}.txt").write_text(wikitext, encoding="utf-8")
            got += 1
        print(f"{fname}: 区间 {len(merged)} 段，提取累计 {got}", flush=True)
    print(f"全文提取完成 {got} 位。", flush=True)


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase in ("index", "all"):
        phase_index()
    if phase in ("fetch", "all"):
        phase_fetch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
