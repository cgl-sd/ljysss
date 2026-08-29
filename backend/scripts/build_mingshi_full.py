#!/usr/bin/env python3
"""把全本《明史》文本定形为逐卷文件：去重复块、剥模板残留、拼接硬换行。

原始文件（项目根的 ming_histroy.txt）是 HTML 转出的文本，有四处必须处理才能当主源：
段落实行按固定宽度硬换行（一句被劈成两行）、残留 `</div>` 与 `------------` 分隔线、
表部十三卷正文只有「（略）」、以及末尾拼进了一大段与前文逐行重复的内容。

    backend/.venv/bin/python backend/scripts/build_mingshi_full.py [--src 路径]

输出 backend/sources/mingshi_full/卷NNN.txt（UTF-8，每段一行）与 manifest.json。
表部与缺卷不在本脚本职责内，由 build_mingshi_corpus.py 从维基文库的表格里补。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html import unescape
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
OUT = BACKEND / "sources" / "mingshi_full"

U = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
HEADER = re.compile(r"^卷([一二三四五六七八九十百]+)[ \t\u3000]*(本纪|志|表|列传)[ \t\u3000]*第?([一二三四五六七八九十百]*)")
DIVIDER = "------------"


def cn2int(text: str) -> int:
    total = num = 0
    for ch in text:
        if ch in U:
            num = U[ch]
        elif ch == "十":
            total += (num or 1) * 10
            num = 0
        elif ch == "百":
            total += (num or 1) * 100
            num = 0
    return total + num


def unescape_all(text: str) -> str:
    """源文件把生僻字实体二次编码过（&amp;lt;），解到不再变化为止。"""

    while True:
        decoded = unescape(text)
        if decoded == text:
            return text
        text = decoded


def load_lines(source: Path) -> list[str]:
    return source.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")


def cut_duplicate_tail(lines: list[str], header_at: list[int]) -> tuple[list[str], int | None]:
    """末卷之后若出现与前文逐行相同的内容，即为拼装重复块，整块切掉。"""

    if not header_at:
        return lines, None
    long_lines = {line.strip() for line in lines[:header_at[-1]] if len(line.strip()) >= 25}
    for index in range(header_at[-1], len(lines)):
        if (text := lines[index].strip()) and len(text) >= 25 and text in long_lines:
            return lines[:index], index + 1
    return lines, None


def paragraphs(block: list[str]) -> list[str]:
    """原文件每行之间都夹着空行，空行不能当段落边界——改按句末标点断段。

    源文本是按固定宽度硬换行的，一句常被劈成两行，所以只在「行末是句末标点」时
    收束一段；行末是别的字就继续连下一行。◎/○ 小节标题各自独立成段。
    这只改变换行位置，不增删任何字。
    """

    out: list[str] = []
    buffer: list[str] = []
    for raw in block:
        line = re.sub(r"</?div[^>]*>", "", raw.strip()).strip()
        if not line or line == DIVIDER.strip("-"):
            continue
        line = unescape_all(line)
        if line.startswith(("◎", "○")):
            if buffer:
                out.append("".join(buffer))
                buffer = []
            out.append(line)
            continue
        buffer.append(line)
        if line.endswith(("。", "！", "？", "：")):
            out.append("".join(buffer))
            buffer = []
    if buffer:
        out.append("".join(buffer))
    return [p for p in out if p != "（略）"]


def build(source: Path) -> dict:
    lines = load_lines(source)
    marks = [(index, cn2int(m.group(1)), m.group(2), m.group(3))
             for index, raw in enumerate(lines) if (m := HEADER.match(raw))]
    if not marks:
        raise SystemExit("没找到任何卷标题，检查源文件编码与标题格式。")

    lines, cut_at = cut_duplicate_tail(lines, [i for i, *_ in marks])
    marks = [(index, num, kind, ordinals) for index, num, kind, ordinals in marks
             if index < len(lines)]

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("卷*.txt"):
        old.unlink()

    manifest: dict[str, object] = {"源文件": source.name, "重复块切断于行": cut_at, "卷": {}}
    bounds = [m[0] for m in marks] + [len(lines)]
    for (index, num, kind, ordinal), stop in zip(marks, bounds[1:]):
        body = paragraphs(lines[index + 1:stop])
        text = f"卷{num} {kind}{ordinal}\n" + "\n".join(body)
        (OUT / f"卷{num:03d}.txt").write_text(text + "\n", encoding="utf-8")
        manifest["卷"][str(num)] = {"部类": kind, "段落": len(body), "字数": sum(len(p) for p in body)}

    counts = [v["字数"] for v in manifest["卷"].values()]
    manifest["统计"] = {
        "卷数": len(counts), "总字数": sum(counts),
        "空卷(表部「（略）」等)": [j for j, v in manifest["卷"].items() if v["字数"] < 400],
        "缺卷": sorted(set(range(1, 333)) - {int(k) for k in manifest["卷"]}),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def supplement() -> list[tuple[int, int, str]]:
    """全本缺的部分从维基文库补：表部十三卷（全本正文只有「（略）」）、卷330–332、历九。

    表部的价值正在那张表——诸王/功臣/外戚世系与宰辅七卿年表，是从封号谥号
    反查本名（「代简王桂」→「朱桂」）的映射源，用整行文字无法获得。
    """

    sys.path.insert(0, str(BACKEND / "scripts"))
    from build_mingshi_corpus import fetch_juan

    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    thin = [int(k) for k, v in manifest["卷"].items() if v["字数"] < 400]
    wanted = sorted(set(thin) | {int(k) for k in manifest["统计"]["缺卷"]})
    results: list[tuple[int, int, str]] = []
    for juan in wanted:
        text, note = "", "失败"
        for attempt in range(3):
            try:
                text = fetch_juan(juan)
                note = "维基文库"
                break
            except Exception as error:
                note = f"失败（{type(error).__name__}）"
                time.sleep(3 * (attempt + 1))
        body = [line for line in text.split("\n") if line.strip() and line.strip() != "（略）"]
        if len("".join(body)) < 400:
            note += "·内容亦缺"
        else:
            (OUT / f"卷{juan:03d}.txt").write_text(f"卷{juan}\n" + "\n".join(body) + "\n", encoding="utf-8")
        results.append((juan, len("".join(body)), note))

    # 补卷改变了语料构成，重新汇总 manifest，避免统计停留在补卷之前。
    for path in sorted(OUT.glob("卷*.txt")):
        juan = int(path.stem[1:])
        lines = path.read_text(encoding="utf-8").split("\n")
        body = [line for line in lines[1:] if line.strip()]
        entry = manifest["卷"].setdefault(str(juan), {"部类": "表" if 100 <= juan <= 112 else "列传"})
        entry["段落"] = len(body)
        entry["字数"] = sum(len(line) for line in body)
    manifest["统计"] = {
        "卷数": len(manifest["卷"]),
        "总字数": sum(v["字数"] for v in manifest["卷"].values()),
        "空卷(表部「（略）」等)": [j for j, v in manifest["卷"].items() if v["字数"] < 400],
        "缺卷": sorted(set(range(1, 333)) - {int(k) for k in manifest["卷"]}),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=OUT / "ming_histroy.txt")
    parser.add_argument("--supplement", action=argparse.BooleanOptionalAction, default=True,
                        help="缺卷与表部从维基文库补（默认开启；关闭会把已补的 17 卷清空）")
    args = parser.parse_args()
    info = build(args.src)
    stats = info["统计"]
    print(f"定形完成：{stats['卷数']} 卷，{stats['总字数']:,} 字 → {OUT.relative_to(ROOT)}")
    print(f"待补卷: {sorted(set(int(j) for j in stats['空卷(表部「（略）」等)']) | set(stats['缺卷']))}")
    if args.supplement:
        print("\n从维基文库补卷（表格按行转文字）：")
        for juan, size, note in supplement():
            print(f"  卷{juan:>3}: {size:>7,} 字  {note}")
        leftover = [int(k) for k, v in json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["卷"].items()
                    if v["字数"] < 400]
        print(f"\n补卷后仍单薄的卷: {sorted(leftover) or '无'}")
