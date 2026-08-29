#!/usr/bin/env python3
"""内容库文本化命令行：库 ↔ data/content/*.jsonl。

二进制库不进版本库，内容真相是按表切分的一行一条 JSONL——可 diff、可 review、
可跨机器重建。表清单、排序键与读写实现都在 app.database，服务启动时若发现库缺失
会自动从文本重建，因此新克隆无需额外步骤。

    .venv/bin/python scripts/content_store.py export   # 库 → 文本
    .venv/bin/python scripts/content_store.py import   # 文本 → 库
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import export_content, import_content  # noqa: E402


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in {"export", "import"}:
        raise SystemExit(__doc__)
    for table, count in (export_content() if action == "export" else import_content()):
        print(f"{table:<24}{count:>6} 行")


if __name__ == "__main__":
    main()
