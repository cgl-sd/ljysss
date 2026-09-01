#!/usr/bin/env python3
"""人物肖像的生成清单、导入与体积校验。

人物库与应用资源以同一套稳定键连接：``portrait_<person_id>.webp``。
生成清单直接读取已校验的维基全文存档、人物生平与来源登记，避免批量生图时
再次以同名检索误配人物。导入命令只接受规范文件名，并把图片压缩为 App 用 WebP。

示例：
    python3 backend/scripts/portrait_pipeline.py manifest
    python3 backend/scripts/portrait_pipeline.py import --input tmp/portrait-import
    python3 backend/scripts/portrait_pipeline.py audit
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIRECTORY = ROOT / "backend" / "data" / "content"
DRAWABLE_DIRECTORY = ROOT / "app" / "src" / "main" / "res" / "drawable"
PORTRAIT_DIRECTORY = ROOT / "app" / "src" / "main" / "res" / "drawable-nodpi"
DEFAULT_IMPORT_DIRECTORY = ROOT / "tmp" / "portrait-import"
DEFAULT_MANIFEST = ROOT / "docs" / "portrait-generation-list.csv"

TARGET_WIDTH = 320
TARGET_HEIGHT = 480
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT
TARGET_QUALITY = 78
MIN_QUALITY = 60
TARGET_BYTES = 72 * 1024
MAX_BYTES = 96 * 1024
ALLOWED_INPUT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

STYLE = (
    "明代人物绢本肖像插绘；工笔线描、细密木刻肌理和暖褐色宣纸底；"
    "青黛、赭石、暗金的低饱和配色；庄重、克制、非摄影写实。"
)
NEGATIVE_PROMPT = (
    "现代服装、现代发型、摄影、欧美面孔、奇幻盔甲、戏曲脸谱、夸张战斗动作、"
    "不确定的官阶补子、文字、姓名题字、印章、水印、logo、边框、多人、"
    "错误朝代服饰、过度鲜艳配色。"
)


def read_jsonl(name: str) -> list[dict[str, Any]]:
    path = CONTENT_DIRECTORY / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(name: str, rows: Iterable[dict[str, Any]]) -> None:
    path = CONTENT_DIRECTORY / name
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def resource_stem(person_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9-]+", person_id):
        raise ValueError(f"非法人物资源键：{person_id}")
    escaped = "".join(
        character
        if character.islower() or character.isdigit()
        else f"_u_{character.lower()}_"
        if character.isupper()
        else "_d_"
        for character in person_id
    )
    return f"portrait_{escaped}"


def resource_filename(person_id: str) -> str:
    return f"{resource_stem(person_id)}.webp"


def source_assets(person: dict[str, Any]) -> list[Path]:
    """返回已存在的标准图；旧 PNG 仅认已登记的画像，避免同拼音人物串图。"""
    canonical = [
        path for path in PORTRAIT_DIRECTORY.glob(f"{resource_stem(person['id'])}.*")
        if path.suffix.lower() in ALLOWED_INPUT_SUFFIXES
    ]
    if canonical or not person.get("portrait_key"):
        return canonical
    legacy_stem = f"portrait_{person['id'].lower().replace('-', '_')}"
    return [
        path for path in DRAWABLE_DIRECTORY.glob(f"{legacy_stem}.*")
        if path.suffix.lower() in ALLOWED_INPUT_SUFFIXES
    ]


def first_prose(text: str, limit: int = 220) -> str:
    """取已存档正文的开篇事实，不把章节名和家族名录送进生图提示词。"""
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", text)]
    prose = []
    for paragraph in paragraphs:
        if not paragraph or len(paragraph) < 14:
            continue
        if re.fullmatch(r"[一-龥]{1,8}", paragraph):
            continue
        prose.append(paragraph)
        if len("".join(prose)) >= limit:
            break
    compact = "".join(prose)
    if len(compact) <= limit:
        return compact
    boundary = max(compact.rfind(mark, 0, limit) for mark in "。；；")
    return compact[: boundary + 1 if boundary >= limit // 2 else limit].strip()


def role_description(category: str, title: str) -> str:
    if category == "帝王":
        return "明代储君" if "太子" in title else "明代帝王"
    if category == "内廷":
        if any(token in title for token in ("皇后", "太后", "妃", "嫔", "夫人", "公主", "郡主")):
            return "明代宫廷女性"
        if any(token in title for token in ("太监", "宦官", "中官", "司礼监")):
            return "明代宦官"
        return "明代内廷人物"
    if category == "宗藩":
        return "明代宗室女性" if any(token in title for token in ("公主", "郡主", "王妃")) else "明代宗室或藩王"
    if category == "朝臣":
        return "明代文官"
    if category == "将帅":
        return "明代将帅"
    return "明代文人或学者"


def clothing_instruction(category: str, title: str) -> str:
    if category == "帝王":
        return "服制符合正式称号；储君不用皇帝龙袍，皇帝纹样与陈设保持节制"
    if category == "内廷":
        return "礼服、发饰与首饰只与正式称号相称，不采用戏曲化妆"
    if category == "宗藩":
        return "使用与封号相称的礼服或常服，避免僭用皇帝纹样"
    if category == "朝臣":
        return "乌纱帽与官服符合文官身份；官阶细节不确定时从简，不臆造补子"
    if category == "将帅":
        return "布面甲、罩袍或武官常服，沉稳坐姿或站姿，不表现战斗场景"
    return "素雅士人袍服，可配书卷、砚台或淡雅书斋背景"


def source_index() -> tuple[dict[str, str], dict[str, list[dict[str, str]]], dict[str, str]]:
    wiki = {row["person_id"]: row.get("full_text", "") for row in read_jsonl("person_wiki.jsonl")}
    references: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_jsonl("content_reference.jsonl"):
        if row.get("content_type") == "person":
            references[row["content_id"]].append(row)
    life = {
        row["person_id"]: row.get("content", "")
        for row in read_jsonl("person_section.jsonl")
        if row.get("section_key") == "life"
    }
    return wiki, references, life


def reference_text(rows: list[dict[str, str]]) -> tuple[str, str]:
    labels: list[str] = []
    urls: list[str] = []
    for row in rows:
        title = row.get("title", "").strip()
        url = row.get("url", "").strip()
        if title and title not in labels:
            labels.append(title)
        if url and url not in urls:
            urls.append(url)
    return "；".join(labels[:3]), " | ".join(urls[:3])


def narrative_summary(person: dict[str, Any], wiki: dict[str, str], life: dict[str, str]) -> tuple[str, str]:
    online = first_prose(wiki.get(person["id"], ""))
    local = first_prose(life.get(person["id"], "") or person.get("biography", ""))
    if online and local and online != local:
        return online, local
    return online or local, ""


def portrait_prompt(person: dict[str, Any], online: str, local: str) -> str:
    identity = f"{role_description(person['category'], person['title'])}「{person['display_name']}」"
    known_facts = online or local or "仅依据正式称号、分类、年号与生卒信息作保守还原"
    return (
        "Use case: historical-scene\n"
        "Asset type: Android 人物卡片单人肖像\n"
        f"Primary request: 为{identity}制作单人半身肖像。正式称号：{person['title']}；"
        f"活动年号：{person['reign'] or '未详'}；生卒：{person['years'] or '未详'}。\n"
        f"Verified historical context: {known_facts}\n"
        f"Style/medium: {STYLE}\n"
        "Composition/framing: 竖幅 2:3，单人、正面或微侧面半身，头顶与肩部完整留出安全边距，"
        "脸部位于画面上半部，人物居中，不出现任何文字。\n"
        f"Constraints: {clothing_instruction(person['category'], person['title'])}；"
        "无可靠传世像时不虚构可识别的真实面貌，只呈现与身份、时代相符的成年汉人概括性形象。\n"
        f"Avoid: {NEGATIVE_PROMPT}"
    )


def manifest(output: Path) -> int:
    people = read_jsonl("person.jsonl")
    wiki, references, life = source_index()
    people_without_assets = [person for person in people if not source_assets(person)]
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "person_id", "人名", "显示名", "分类", "正式称号", "活动年号", "生卒", "字或号",
        "输出文件名", "生成画布", "导入格式", "目标体积", "线上资料摘要", "现有介绍摘要",
        "来源登记", "来源链接", "生图提示词", "负面提示词", "验收条件",
    )
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for person in people_without_assets:
            online, local = narrative_summary(person, wiki, life)
            labels, urls = reference_text(references.get(person["id"], []))
            writer.writerow(
                {
                    "person_id": person["id"],
                    "人名": person["name"],
                    "显示名": person["display_name"],
                    "分类": person["category"],
                    "正式称号": person["title"],
                    "活动年号": person.get("reign", ""),
                    "生卒": person.get("years", ""),
                    "字或号": person.get("courtesy_name", ""),
                    "输出文件名": resource_filename(person["id"]),
                    "生成画布": "竖幅 2:3，建议 1024×1536 px",
                    "导入格式": "320×480 px WebP（自动转换）",
                    "目标体积": "目标 ≤72 KB；硬上限 96 KB",
                    "线上资料摘要": online,
                    "现有介绍摘要": local,
                    "来源登记": labels,
                    "来源链接": urls,
                    "生图提示词": portrait_prompt(person, online, local),
                    "负面提示词": NEGATIVE_PROMPT,
                    "验收条件": "单人；无文字、印章、水印或边框；明代服饰与正式称号相称；"
                    "竖幅 2:3；脸部清晰且位于上半部；文件名必须与输出文件名完全一致。",
                }
            )
    return len(people_without_assets)


def command_available(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"缺少图片处理程序：{name}")
    return path


def image_dimensions(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        [command_available("sips"), "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    values = dict(re.findall(r"pixel(Width|Height):\s*(\d+)", result.stdout))
    return int(values["Width"]), int(values["Height"])


def transcode(source: Path, destination: Path, replace: bool, allow_legacy_crop: bool = False) -> int:
    width, height = image_dimensions(source)
    ratio = width / height
    if not allow_legacy_crop and not 0.61 <= ratio <= 0.72:
        raise ValueError(f"{source.name} 的比例为 {width}×{height}，不是竖幅 2:3")
    if destination.exists() and not replace:
        raise ValueError(f"目标已存在：{destination}（如需替换请使用 --replace）")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ljysss-portrait-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        scaled = temporary_root / "scaled.png"
        crop = temporary_root / "crop.png"
        resize_argument = "--resampleHeight" if ratio >= TARGET_RATIO else "--resampleWidth"
        resize_value = str(TARGET_HEIGHT if ratio >= TARGET_RATIO else TARGET_WIDTH)
        subprocess.run(
            [command_available("sips"), resize_argument, resize_value, str(source), "--out", str(scaled)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                command_available("sips"), "--cropToHeightWidth", str(TARGET_HEIGHT), str(TARGET_WIDTH),
                str(scaled), "--out", str(crop),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        selected: tuple[int, Path] | None = None
        for quality in range(TARGET_QUALITY, MIN_QUALITY - 1, -4):
            temporary = destination.with_name(f".{destination.stem}-q{quality}.webp")
            subprocess.run(
                [command_available("cwebp"), "-quiet", "-mt", "-q", str(quality), str(crop), "-o", str(temporary)],
                check=True,
            )
            if temporary.stat().st_size <= MAX_BYTES:
                selected = quality, temporary
                break
            temporary.unlink()
    if selected is None:
        raise ValueError(f"{source.name} 即使降至质量 {MIN_QUALITY} 仍超过 {MAX_BYTES // 1024} KB")
    quality, temporary = selected
    temporary.replace(destination)
    return quality


def import_portraits(input_directory: Path, replace: bool) -> int:
    people = read_jsonl("person.jsonl")
    by_stem = {resource_stem(person["id"]): person for person in people}
    candidates = [path for path in sorted(input_directory.iterdir()) if path.suffix.lower() in ALLOWED_INPUT_SUFFIXES]
    if not candidates:
        raise SystemExit(f"未发现待导入画像：{input_directory}")
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in candidates:
        grouped[path.stem].append(path)
    problems: list[str] = []
    for stem, paths in grouped.items():
        if stem not in by_stem:
            problems.append(f"未知文件名：{paths[0].name}")
        elif len(paths) != 1:
            problems.append(f"同一人物有多个候选图片：{', '.join(path.name for path in paths)}")
    if problems:
        raise SystemExit("\n".join(problems))

    updated_ids: set[str] = set()
    for stem, paths in grouped.items():
        person = by_stem[stem]
        destination = PORTRAIT_DIRECTORY / resource_filename(person["id"])
        if destination.exists() and not replace:
            continue
        transcode(paths[0], destination, replace=replace)
        updated_ids.add(person["id"])

    for person in people:
        if person["id"] in updated_ids:
            person["portrait_key"] = resource_stem(person["id"])
    write_jsonl("person.jsonl", people)
    return len(updated_ids)


def audit() -> int:
    people = read_jsonl("person.jsonl")
    assets = list(PORTRAIT_DIRECTORY.glob("portrait_*.webp"))
    asset_stems = {asset.stem for asset in assets}
    expected_stems = {resource_stem(person["id"]) for person in people if person.get("portrait_key")}
    unknown = sorted(asset_stems - {resource_stem(person["id"]) for person in people})
    missing = sorted(expected_stems - asset_stems)
    oversized = [asset for asset in assets if asset.stat().st_size > MAX_BYTES]
    print(f"人物总数：{len(people)}")
    print(f"已导入 WebP：{len(assets)}")
    print(f"WebP 总体积：{sum(asset.stat().st_size for asset in assets) / 1024 / 1024:.2f} MB")
    print(f"缺少已登记资源：{len(missing)}")
    print(f"未知资源：{len(unknown)}")
    print(f"超过 {MAX_BYTES // 1024} KB：{len(oversized)}")
    if missing or unknown or oversized:
        return 1
    return 0


def migrate_legacy(replace: bool) -> int:
    """把已登记的旧 PNG/JPG 转为标准 WebP，供首次统一资源规格使用。"""
    people = read_jsonl("person.jsonl")
    migrated_ids: set[str] = set()
    for person in people:
        if not person.get("portrait_key"):
            continue
        legacy_stem = f"portrait_{person['id'].lower().replace('-', '_')}"
        candidates = [
            path for path in DRAWABLE_DIRECTORY.glob(f"{legacy_stem}.*")
            if path.suffix.lower() in ALLOWED_INPUT_SUFFIXES
        ]
        if len(candidates) != 1:
            raise SystemExit(f"{person['display_name']} 的旧画像应为一张，实际为 {len(candidates)} 张")
        transcode(
            candidates[0],
            PORTRAIT_DIRECTORY / resource_filename(person["id"]),
            replace=replace,
            allow_legacy_crop=True,
        )
        person["portrait_key"] = resource_stem(person["id"])
        migrated_ids.add(person["id"])
    write_jsonl("person.jsonl", people)
    return len(migrated_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description="明代人物肖像批量处理")
    commands = parser.add_subparsers(dest="command", required=True)
    manifest_parser = commands.add_parser("manifest", help="导出缺图人物的生图清单")
    manifest_parser.add_argument("--output", type=Path, default=DEFAULT_MANIFEST)
    import_parser = commands.add_parser("import", help="压缩并导入待处理肖像")
    import_parser.add_argument("--input", type=Path, default=DEFAULT_IMPORT_DIRECTORY)
    import_parser.add_argument("--replace", action="store_true", help="允许替换同名 WebP")
    migrate_parser = commands.add_parser("migrate-legacy", help="把已登记的旧 PNG/JPG 转为标准 WebP")
    migrate_parser.add_argument("--replace", action="store_true", help="允许替换同名 WebP")
    commands.add_parser("audit", help="校验已导入 WebP 与人物库")
    args = parser.parse_args()
    if args.command == "manifest":
        print(f"已导出 {manifest(args.output)} 位缺图人物：{args.output}")
        return 0
    if args.command == "import":
        print(f"已导入 {import_portraits(args.input, args.replace)} 张人物肖像。")
        return 0
    if args.command == "migrate-legacy":
        print(f"已统一 {migrate_legacy(args.replace)} 张既有肖像。")
        return 0
    return audit()


if __name__ == "__main__":
    raise SystemExit(main())
