#!/usr/bin/env python3
"""从内容库生成汉字→拼音对照表 Kotlin 文件（搜索拼音匹配用）。

用法: .venv/bin/python scripts/generate_pinyin_table.py

输出: app/src/main/java/com/ljyss/domain/PinyinTable.kt（生成文件，勿手改）。
拼音取 pypinyin NORMAL 默认读音；生僻/多音字以常见读法为准，属已知边界。
"""
import json
import re
from pathlib import Path

from pypinyin import Style, pinyin

ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT = ROOT / "backend" / "data" / "content"
OUT = ROOT / "app" / "src" / "main" / "java" / "com" / "ljyss" / "domain" / "PinyinTable.kt"

HAN = re.compile(r"[\u4e00-\u9fff]")

chars = set()
for path in sorted(CONTENT.glob("*.jsonl")):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = json.dumps(obj, ensure_ascii=False)
        chars.update(HAN.findall(text))

table = {}
for ch in sorted(chars):
    py = pinyin(ch, style=Style.NORMAL, errors="default")[0][0].strip()
    table[ch] = py

lines = [
    "package com.ljyss.domain",
    "",
    "/**",
    " * 汉字→拼音对照表（生成文件，勿手改）。",
    f" * 由 backend/scripts/generate_pinyin_table.py 生成；共 {len(table)} 字，拼音取 pypinyin NORMAL 默认读音。",
    " * 多音字以常见读法为准；未收录汉字原样返回。",
    " */",
    "internal object PinyinTable {",
    "    private val data: String = \"\"\"",
]
for ch in sorted(table):
    lines.append(f"{ch}={table[ch]}")
lines += [
    '    """',
    "",
    "    private val map: Map<Char, String> by lazy {",
    "        data.lineSequence().mapNotNull { line ->",
    "            val idx = line.indexOf('=')",
    "            if (idx > 0) line[0] to line.substring(idx + 1) else null",
    "        }.toMap()",
    "    }",
    "",
    "    fun pinyinOf(ch: Char): String? = map[ch]",
    "}",
    "",
]
OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"written {OUT} ({len(table)} chars)")
