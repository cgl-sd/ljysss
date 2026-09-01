#!/usr/bin/env python3
"""发布前校验机构与典章正文、关联和逐条资源。"""

from __future__ import annotations

import json
import hashlib
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - validator can still report a useful error
    Image = None

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "backend" / "data" / "content"
RESOURCES = ROOT / "app" / "src" / "main" / "res" / "drawable-nodpi"
BAD_TEXT = re.compile(r"[A-Za-z]|旅游|景区|博物馆|世界文化遗产|文物保护单位|非物质文化遗产|外文|英文|拉丁|转写|现为|管理中心")


def rows(table: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def perceptual_hash(path: Path) -> str | None:
    """轻量感知哈希：不依赖第三方 imagehash，足以发现误绑定的同一张图。"""
    if Image is None:
        return None
    with Image.open(path) as image:
        source = image.convert("RGB")
        gray = source.convert("L").resize((16, 16), Image.Resampling.BILINEAR)
        pixels = list(gray.getdata())
        color_pixels = list(source.resize((8, 8), Image.Resampling.BILINEAR).getdata())
    average = sum(pixels) / len(pixels)
    luminance = "".join("1" if pixel >= average else "0" for pixel in pixels)
    # 保留粗粒度色相，避免不同条目的线描在灰度下偶然碰撞。
    chroma = "".join(f"{r // 32:02x}{g // 32:02x}{b // 32:02x}" for r, g, b in color_pixels)
    return luminance + chroma


def main() -> int:
    institutions = rows("institution")
    institution_sections = rows("institution_section")
    institution_people = rows("institution_person")
    specials = rows("special_item")
    special_sections = rows("special_section")
    special_people = rows("special_person")
    people = rows("person")
    errors: list[str] = []
    for table, records in (("institution", institutions), ("special_item", specials)):
        ids = [record.get("id", "") for record in records]
        names = [record.get("name", "").strip() for record in records]
        if not all(ids) or len(ids) != len(set(ids)):
            errors.append(f"{table}存在空或重复 ID")
        if not all(names) or len(names) != len(set(names)):
            errors.append(f"{table}存在空或重复名称")
        for record in records:
            if not record.get("source_id", "").strip():
                errors.append(f"{table}:{record.get('id')}缺少内部来源标识")
    for table, records, key in (("institution_section", institution_sections, "institution_id"), ("special_section", special_sections, "special_item_id")):
        grouped: dict[str, list[dict]] = defaultdict(list)
        for record in records:
            grouped[record[key]].append(record)
            if len(record.get("content", "").strip()) < 50:
                errors.append(f"{table}:{record[key]}正文过短")
            if BAD_TEXT.search(record.get("content", "")):
                errors.append(f"{table}:{record[key]}含禁用文字")
        for item_id, group in grouped.items():
            positions = [record.get("position") for record in group]
            if len(group) < 2 or len({record["content"] for record in group}) != len(group):
                errors.append(f"{table}:{item_id}分栏少于两栏或重复")
            if len(positions) != len(set(positions)) or positions != sorted(positions):
                errors.append(f"{table}:{item_id}分栏顺序不稳定")
            if len({record.get("title", "").strip() for record in group}) != len(group):
                errors.append(f"{table}:{item_id}分栏标题重复")
            if any(not record.get("source_id", "").strip() for record in group):
                errors.append(f"{table}:{item_id}分栏缺少内部来源标识")
    all_assets: list[str] = []
    for table, records, key in (("institution", institutions, "id"), ("special_item", specials, "id")):
        assets = [record.get("image_asset", "") for record in records]
        all_assets.extend(assets)
        if len(assets) != len(set(assets)):
            errors.append(f"{table}存在重复图片资源")
        for record in records:
            asset_path = RESOURCES / f"{record.get('image_asset', '')}.webp"
            if not record.get("image_asset") or not asset_path.is_file():
                errors.append(f"{table}:{record[key]}缺少专属图片")
            elif Image is not None:
                try:
                    with Image.open(asset_path) as image:
                        if image.size != (768, 512) or image.format != "WEBP":
                            errors.append(f"{table}:{record[key]}图片规格不是768×512 WebP")
                        image.verify()
                except Exception as exc:
                    errors.append(f"{table}:{record[key]}图片无法读取：{exc}")
            value = " ".join(str(record.get(field, "")) for field in ("name", "function", "description"))
            if BAD_TEXT.search(value):
                errors.append(f"{table}:{record[key]}摘要含禁用文字")
    asset_paths = [RESOURCES / f"{asset}.webp" for asset in all_assets]
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in asset_paths if path.is_file()]
    if len(hashes) != len(set(hashes)):
        errors.append("正式条目存在完全相同的图片文件")
    perceptual_hashes = [value for path in asset_paths if path.is_file() for value in [perceptual_hash(path)] if value]
    if len(perceptual_hashes) != len(set(perceptual_hashes)):
        errors.append("正式条目存在感知哈希相同的图片文件")
    manifest_path = CONTENT / "world_asset_manifest.jsonl"
    if manifest_path.is_file():
        manifest = rows("world_asset_manifest")
        if len(manifest) != len(all_assets) or {entry.get("asset") for entry in manifest} != {f"{asset}.webp" for asset in all_assets}:
            errors.append("图片清单与正式条目不一致")
        for entry in manifest:
            if not all(str(entry.get(field, "")).strip() for field in ("item_id", "name", "visual_subject", "scene", "content_brief", "prompt")):
                errors.append(f"图片清单:{entry.get('asset')}缺少内容驱动的画面说明")
            if entry.get("width") != 768 or entry.get("height") != 512 or entry.get("format") != "WEBP":
                errors.append(f"图片清单:{entry.get('asset')}规格记录错误")
    else:
        errors.append("缺少图片清单")
    person_ids = {person["id"] for person in people}
    for table, records, owner_key in (("institution_person", institution_people, "institution_id"), ("special_person", special_people, "special_item_id")):
        pairs: set[tuple[str, str]] = set()
        for record in records:
            if record.get("person_id") not in person_ids:
                errors.append(f"{table}:{record.get('person_id')}指向不存在的人物")
            pair = (record.get(owner_key, ""), record.get("person_id", ""))
            if pair in pairs:
                errors.append(f"{table}:{pair[0]}存在重复人物关联")
            pairs.add(pair)
            if not record.get("source_id", "").strip():
                errors.append(f"{table}:{pair[0]}缺少内部来源标识")
    database = ROOT / "backend" / "data" / "ming_history.sqlite3"
    with sqlite3.connect(database) as connection:
        expected = {"institution": len(institutions), "institution_section": len(institution_sections), "special_item": len(specials), "special_section": len(special_sections)}
        for table, count in expected.items():
            actual = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if actual != count:
                errors.append(f"SQLite {table}={actual}，JSONL={count}")
    if errors:
        for error in errors:
            print("错误：" + error)
        return 1
    print(f"校验通过：机构 {len(institutions)} 条、典章 {len(specials)} 条、专属图片 {len(institutions) + len(specials)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
