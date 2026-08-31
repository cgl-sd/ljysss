#!/usr/bin/env python3
"""为机构、典章生成逐条对应的轻量矢量示意图。

资源不是分类占位图：文件名由条目 id 派生，每条记录都有独立配色和构图，
Android 以 image_asset 按条目读取。这样在没有可靠历史照片时也不会错误复用别的对象。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "backend" / "data" / "content"
OUT = ROOT / "app" / "src" / "main" / "res" / "drawable-nodpi"


def rows(table: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def palette(key: str) -> tuple[str, str, str]:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    # 明式宣纸、朱砂和青黛的低饱和组合；哈希确保每个条目颜色不同。
    paper = (int(digest[0:2], 16) % 18 + 232, int(digest[2:4], 16) % 16 + 222, int(digest[4:6], 16) % 14 + 202)
    ink = (int(digest[6:8], 16) % 36 + 88, int(digest[8:10], 16) % 30 + 55, int(digest[10:12], 16) % 28 + 38)
    vermilion = (int(digest[12:14], 16) % 35 + 150, int(digest[14:16], 16) % 28 + 38, int(digest[16:18], 16) % 20 + 25)
    return "#%02x%02x%02x" % paper, "#%02x%02x%02x" % ink, "#%02x%02x%02x" % vermilion


def motif(category: str, ink: str, vermilion: str) -> str:
    if category in {"军事卫所"}:
        return f'<path android:fillColor="{ink}" android:pathData="M160,28L238,67v47c0,31 -34,56 -78,68 -44,-12 -78,-37 -78,-68V67z"/><path android:fillColor="{vermilion}" android:pathData="M146,61h28v68h-28zM121,87h78v16h-78z"/>'
    if category in {"内廷宦官"}:
        return f'<path android:fillColor="{ink}" android:pathData="M90,138V80l70,-48 70,48v58h-24V94h-92v44z"/><path android:fillColor="{vermilion}" android:pathData="M137,138V92h46v46z"/>'
    if category in {"监察司法"}:
        return f'<path android:fillColor="{ink}" android:pathData="M154,34h12v106h-12zM94,60h132v10H94zM72,68h54l-18,42H90zM194,68h54l-18,42h-38z"/><path android:fillColor="{vermilion}" android:pathData="M74,123h52v12H74zM194,123h52v12h-52z"/>'
    if category in {"地方治理"}:
        return f'<path android:fillColor="{ink}" android:pathData="M38,56C78,34 101,77 138,54S202,42 282,64v58c-54,15 -79,-12 -126,13S84,145 38,124z"/><path android:fillColor="{vermilion}" android:pathData="M48,86h224v8H48zM156,48h8v86h-8z"/>'
    if category in {"教育与专门"}:
        return f'<path android:fillColor="{ink}" android:pathData="M45,52l115,-24 115,24 -115,24zM58,66h204v70H58z"/><path android:fillColor="{vermilion}" android:pathData="M88,78h18v44H88zM151,78h18v44h-18zM214,78h18v44h-18z"/>'
    if category in {"制度"}:
        return f'<path android:fillColor="{ink}" android:pathData="M78,45h164v95H78z"/><path android:fillColor="{vermilion}" android:pathData="M100,63h120v9H100zM100,85h120v9H100zM100,107h84v9h-84z"/>'
    if category in {"器物"}:
        return f'<path android:fillColor="{ink}" android:pathData="M103,48h114v20h-12v55c0,19 -20,31 -45,31s-45,-12 -45,-31V68h-12z"/><path android:fillColor="{vermilion}" android:pathData="M88,47h144v12H88zM137,36h46v11h-46z"/>'
    return f'<path android:fillColor="{ink}" android:pathData="M48,132V75l112,-48 112,48v57h-28V91H76v41z"/><path android:fillColor="{vermilion}" android:pathData="M119,132V91h82v41z"/>'


def render(item: dict, kind: str) -> str:
    background, ink, red = palette(kind + ":" + item["id"])
    name = "world_" + kind + "_" + item["id"].replace("-", "_")
    category = item.get("category", "")
    return f'''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="320dp" android:height="180dp" android:viewportWidth="320" android:viewportHeight="180">
    <path android:fillColor="{background}" android:pathData="M0,0h320v180H0z"/>
    <path android:fillColor="@android:color/transparent" android:strokeColor="{red}" android:strokeWidth="3" android:pathData="M8,8h304v164H8z"/>
    {motif(category, ink, red)}
    <path android:fillColor="@android:color/transparent" android:strokeColor="{red}" android:strokeWidth="2" android:pathData="M22,154h276"/>
</vector>
'''


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    items = [(row, "institution") for row in rows("institution")] + [(row, "special") for row in rows("special_item")]
    for row, kind in items:
        (OUT / f"world_{kind}_{row['id'].replace('-', '_')}.xml").write_text(render(row, kind), encoding="utf-8")
    print(f"生成逐条矢量资源 {len(items)} 个")


if __name__ == "__main__":
    main()
