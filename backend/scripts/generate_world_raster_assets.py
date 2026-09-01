#!/usr/bin/env python3
"""生成机构与典章逐条对应的明式资料画（768×512 WebP）。"""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "backend" / "data" / "content"
OUT = ROOT / "app" / "src" / "main" / "res" / "drawable-nodpi"
SIZE = (768, 512)
BASES = CONTENT / "world_image_bases"
STYLE_REFERENCE = BASES / "officials.png"
STYLE_ARTIFACT = BASES / "artifacts.png"
STYLE_TOMB = BASES / "architecture.png"
STYLE_MILITARY = BASES / "military.png"
STYLE_LOCAL = BASES / "local_governance.png"
STYLE_SCHOLAR = BASES / "education.png"
STYLE_RITUAL = BASES / "rituals.png"


def rows(table: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(seed: str) -> bytes:
    return hashlib.sha1(seed.encode("utf-8")).digest()


def color(seed: str, lo: int, hi: int, alpha: int = 205) -> tuple[int, int, int, int]:
    d = digest(seed)
    if seed.endswith("red") or seed.endswith("bottom"):
        red = lo + d[0] % (hi - lo + 1)
        return (red, max(28, int(red * 0.42)), max(16, int(red * 0.25)), alpha)
    base = lo + d[0] % (hi - lo + 1)
    return (base, max(lo - 12, int(base * 0.82)), max(lo - 22, int(base * 0.62)), alpha)


def parchment(seed: str, base_path: Path = STYLE_REFERENCE) -> Image.Image:
    if base_path.is_file():
        source = Image.open(base_path).convert("RGB")
        d = digest(seed)
        # 同一类资料画以不同的取景窗口呈现，保留原始工笔细节，而不是在图上盖几何图形。
        zoom = 1.06 + (d[0] % 9) / 100
        crop_w, crop_h = int(source.width / zoom), int(source.height / zoom)
        left = int((source.width - crop_w) * (d[1] / 255))
        top = int((source.height - crop_h) * (d[2] / 255))
        image = source.crop((left, top, left + crop_w, top + crop_h)).resize(SIZE, Image.Resampling.LANCZOS)
        image = ImageChops.offset(image, d[0] % 29 - 14, d[1] % 19 - 9)
        image = ImageEnhance.Color(image).enhance(0.68 + d[2] / 255 * 0.22)
        image = ImageEnhance.Contrast(image).enhance(0.86 + d[3] / 255 * 0.14)
        return image
    random.seed(seed)
    image = Image.new("RGB", SIZE, (235, 223, 194))
    draw = ImageDraw.Draw(image, "RGBA")
    for _ in range(8500):
        x, y = random.randrange(SIZE[0]), random.randrange(SIZE[1])
        draw.point((x, y), fill=(120, 98, 65, random.randrange(8, 38)))
    return image.filter(ImageFilter.GaussianBlur(0.45))


def background_lines(draw: ImageDraw.ImageDraw, seed: str) -> None:
    random.seed(seed)
    for y in range(32, SIZE[1] - 20, 28):
        points = [(x, y + random.randrange(-2, 3)) for x in range(20, SIZE[0] - 20, 24)]
        draw.line(points, fill=(67, 53, 37, 52), width=1)


def architecture(draw: ImageDraw.ImageDraw, seed: str, palace: bool) -> None:
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    base = 400 if palace else 420
    draw.polygon([(110, 220), (384, 88), (658, 220)], fill=(87, 66, 44, 145), outline=dark)
    draw.line((110, 220, 658, 220), fill=red, width=5)
    draw.rectangle((145, 220, 623, base), fill=(230, 208, 164, 80), outline=dark, width=4)
    for x in range(176, 612, 86):
        draw.rectangle((x, 228, x + 24, base), fill=(92, 56, 38, 175), outline=dark, width=2)
    for x in range(195, 596, 86):
        draw.rectangle((x, 270, x + 48, 344), fill=(240, 222, 182, 148), outline=dark, width=2)
    draw.rectangle((94, base, 674, base + 26), fill=(95, 67, 44, 180), outline=dark, width=3)
    draw.line((80, base + 28, 688, base + 28), fill=red, width=4)
    if palace:
        draw.ellipse((318, 44, 450, 176), outline=(125, 94, 50, 90), width=3)


def book_or_scroll(draw: ImageDraw.ImageDraw, seed: str, book: bool) -> None:
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    if book:
        draw.polygon([(150, 170), (384, 126), (618, 170), (384, 214)], fill=(91, 70, 45, 155), outline=dark)
        draw.polygon([(150, 170), (384, 214), (384, 385), (150, 335)], fill=(224, 193, 132, 170), outline=dark)
        draw.polygon([(384, 214), (618, 170), (618, 335), (384, 385)], fill=(235, 212, 160, 150), outline=dark)
        for y in range(240, 335, 22):
            draw.line((185, y, 350, y - 24), fill=red, width=2)
            draw.line((416, y - 24, 580, y), fill=red, width=2)
    else:
        draw.ellipse((118, 180, 188, 318), outline=dark, width=5, fill=(197, 154, 88, 145))
        draw.rectangle((152, 180, 615, 318), outline=dark, width=5, fill=(232, 207, 157, 145))
        draw.ellipse((580, 180, 650, 318), outline=dark, width=5, fill=(197, 154, 88, 145))
        for y in range(212, 294, 20):
            draw.line((205, y, 563, y), fill=red, width=2)


def weapon(draw: ImageDraw.ImageDraw, seed: str, cannon: bool) -> None:
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    if cannon:
        draw.ellipse((168, 206, 225, 306), outline=dark, width=4, fill=(111, 76, 42, 170))
        draw.polygon([(208, 204), (594, 248), (596, 305), (210, 322)], fill=(104, 75, 49, 190), outline=dark)
        draw.ellipse((567, 248, 620, 305), outline=red, width=4)
        draw.line((252, 224, 544, 258), fill=(221, 185, 122, 190), width=7)
    else:
        draw.line((184, 374, 582, 126), fill=dark, width=16)
        draw.line((200, 376, 598, 128), fill=red, width=4)
        draw.polygon([(183, 380), (126, 344), (168, 310), (226, 348)], fill=(91, 58, 41, 180), outline=dark)
        draw.ellipse((546, 101, 624, 178), outline=dark, width=5)


def wall_or_tomb(draw: ImageDraw.ImageDraw, seed: str, tomb: bool) -> None:
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    if tomb:
        draw.polygon([(136, 378), (136, 258), (254, 165), (512, 165), (632, 258), (632, 378)], fill=(124, 93, 61, 150), outline=dark)
        draw.polygon([(213, 165), (383, 91), (555, 165)], fill=(99, 72, 50, 160), outline=dark)
        draw.rectangle((324, 272, 442, 378), fill=(229, 205, 159, 180), outline=red, width=4)
        draw.ellipse((356, 306, 410, 361), outline=dark, width=3)
    else:
        points = [(84, 390), (84, 256), (166, 208), (238, 266), (314, 198), (398, 264), (490, 192), (680, 270), (680, 390)]
        draw.line(points, fill=dark, width=18, joint="curve")
        draw.line((84, 356, 680, 356), fill=red, width=4)
        for x in range(120, 660, 78):
            draw.line((x, 330, x + 24, 285), fill=(103, 81, 58, 165), width=3)


def astronomy(draw: ImageDraw.ImageDraw, seed: str) -> None:
    """浑仪与观测台：用于钦天监等专门机构。"""
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    draw.rectangle((142, 346, 626, 384), fill=(112, 82, 50, 145), outline=dark, width=3)
    draw.ellipse((238, 112, 530, 404), outline=dark, width=9)
    draw.ellipse((276, 146, 492, 370), outline=red, width=6)
    draw.ellipse((316, 188, 452, 330), outline=dark, width=5)
    draw.line((255, 344, 512, 168), fill=(105, 75, 45, 170), width=6)
    draw.line((300, 166, 480, 348), fill=(105, 75, 45, 170), width=5)
    for x, y in ((138, 106), (176, 168), (586, 120), (628, 210), (102, 270), (584, 300)):
        draw.ellipse((x, y, x + 9, y + 9), fill=(200, 158, 79, 210))


def officials(draw: ImageDraw.ImageDraw, seed: str, count: int = 3) -> None:
    """朝会与案牍：每项用不同种子决定官员位置与颜色。"""
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    start = 384 - (count - 1) * 70
    for index in range(count):
        x = start + index * 140
        y = 174 + (digest(f"{seed}:{index}")[0] % 25)
        draw.ellipse((x - 24, y, x + 24, y + 47), fill=(80, 59, 40, 180), outline=dark, width=2)
        draw.polygon([(x - 58, y + 96), (x, y + 39), (x + 58, y + 96), (x + 44, y + 220), (x - 44, y + 220)], fill=(178, 49 + (index % 2) * 38, 37, 175), outline=dark)
        draw.rectangle((x - 30, y + 106, x + 30, y + 145), fill=(234, 211, 164, 170), outline=red, width=2)


def commerce(draw: ImageDraw.ImageDraw, seed: str) -> None:
    """漕运、市舶与财政：船、粮袋和平码。"""
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    draw.polygon([(156, 340), (630, 340), (564, 408), (214, 408)], fill=(91, 61, 42, 185), outline=dark)
    draw.line((220, 338, 518, 170), fill=dark, width=7)
    draw.polygon([(306, 228), (510, 294), (510, 184)], fill=(225, 203, 159, 155), outline=red)
    draw.arc((96, 342, 280, 472), 200, 340, fill=(68, 120, 145, 150), width=6)
    draw.arc((490, 348, 684, 470), 200, 340, fill=(68, 120, 145, 150), width=6)
    for x in (170, 230, 580):
        draw.ellipse((x, 280, x + 52, 334), fill=(203, 168, 96, 175), outline=dark, width=2)


def ritual(draw: ImageDraw.ImageDraw, seed: str) -> None:
    """礼制、科举、法令的礼器与卷轴组合。"""
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    draw.ellipse((270, 214, 498, 412), fill=(168, 112, 55, 170), outline=dark, width=5)
    draw.ellipse((313, 256, 455, 370), fill=(232, 210, 165, 145), outline=red, width=4)
    draw.rectangle((156, 172, 264, 352), fill=(230, 207, 162, 175), outline=dark, width=3)
    draw.rectangle((510, 172, 620, 352), fill=(230, 207, 162, 175), outline=dark, width=3)
    for y in range(202, 328, 22):
        draw.line((174, y, 245, y), fill=red, width=2)
        draw.line((528, y, 603, y), fill=red, width=2)


def artifact(draw: ImageDraw.ImageDraw, seed: str) -> None:
    """器物条目的中轴物件构图，避免把实物画成文书。"""
    dark = color(seed, 42, 112)
    red = color(seed + "red", 145, 205)
    d = digest(seed)
    if d[0] % 3 == 0:
        # 炉、瓶、钟等立体器物
        draw.ellipse((274, 142, 494, 220), fill=(133, 93, 55, 185), outline=dark, width=5)
        draw.polygon([(292, 190), (476, 190), (448, 376), (320, 376)], fill=(129, 93, 58, 200), outline=dark)
        draw.ellipse((318, 342, 450, 397), fill=(158, 107, 57, 190), outline=red, width=4)
    elif d[0] % 3 == 1:
        # 玺、印、钱币等平面器物
        draw.rounded_rectangle((242, 172, 526, 388), radius=24, fill=(161, 52, 38, 180), outline=dark, width=5)
        draw.ellipse((312, 228, 456, 348), fill=(232, 204, 150, 175), outline=red, width=4)
    else:
        # 家具、服饰等陈设物
        draw.rectangle((232, 206, 536, 320), fill=(108, 69, 43, 185), outline=dark, width=5)
        for x in (264, 476):
            draw.rectangle((x, 318, x + 30, 408), fill=(99, 63, 40, 180), outline=dark, width=3)
        draw.arc((280, 104, 492, 324), 180, 350, fill=red, width=9)


def visual_subject(item: dict, kind: str, introduction: str) -> tuple[str, str]:
    """从条目名称、类别和真实导语挑选可画的唯一主体与构图。"""
    name = item.get("name", "")
    category = item.get("category", "")
    # 机构分类是已经审核过的强信号，不能被正文中偶然出现的“军”“府”等字覆盖。
    if kind == "institution":
        institutional_scenes = {
            "中枢政务": ("中枢官署、官员与案牍", "officials"),
            "监察司法": ("御史、法案与官署", "officials"),
            "军事卫所": ("明军军阵、旗帜与兵器", "weapon"),
            "内廷宦官": ("宫廷内署与值事场景", "palace"),
            "地方治理": ("地方衙署、城门与文移", "wall"),
            "教育与专门": ("明代学宫、士子与案牍", "architecture"),
        }
        if any(word in name for word in ("钦天", "天文", "观象")):
            return ("浑仪、星图与观测台", "astronomy")
        if any(word in name for word in ("太医", "医学")):
            return ("太医院诊疗与药柜", "officials")
        if any(word in name for word in ("漕运", "市舶", "宝钞", "盐运", "仓")):
            return ("漕船、粮袋与财政文书", "commerce")
        if category in institutional_scenes:
            return institutional_scenes[category]
    if kind == "special" and category == "宫陵":
        if any(word in name for word in ("长城", "城墙", "城防", "关", "城门")):
            return ("城墙、关隘与烽燧", "wall")
        if any(word in name for word in ("陵", "祾恩", "孝陵", "显陵", "祖陵", "景泰陵", "神道")):
            return ("陵寝神道与享殿", "tomb")
        return ("明代宫殿与礼制建筑", "architecture")
    text = f"{name} {category} {introduction}"
    checks = (
        (("钦天", "天文", "历法", "观象"), ("浑仪、星图与观测台", "astronomy")),
        (("太医", "医学", "医药"), ("太医院诊疗与药柜", "officials")),
        (("国子", "翰林", "科举", "书院"), ("明代学宫、士子与案牍", "architecture")),
        (("漕运", "市舶", "宝钞", "户部", "盐", "仓"), ("漕船、粮袋与财政文书", "commerce")),
        (("刑", "大理", "都察", "按察", "司法", "监察"), ("御史、法案与官署", "officials")),
        (("军", "卫", "都督", "兵", "火器", "三大营"), ("明军军阵、旗帜与兵器", "weapon")),
        (("司礼", "内官", "尚膳", "尚衣", "御马", "钟鼓", "兵仗", "织染"), ("宫廷内署与值事场景", "palace")),
        (("布政", "县", "府", "行都司", "地方"), ("地方衙署、城门与文移", "wall")),
        (("长城", "城墙", "城防"), ("城墙、关隘与烽燧", "wall")),
        (("陵", "祾恩", "祖陵", "显陵", "景泰陵"), ("陵寝神道与享殿", "tomb")),
        (("宫", "殿", "坛", "寺", "观", "报恩"), ("明代宫殿与礼制建筑", "architecture")),
        (("炮", "铳", "火器"), ("明代火器的具体形制", "cannon")),
        (("炉", "玺", "玉", "家具", "服饰", "景泰蓝", "货币", "铸"), ("条目所指器物的具体形制", "artifact")),
        (("礼", "制", "法", "赋", "役", "户籍", "卫所"), ("礼器、法令与运行文书", "ritual")),
    )
    for words, subject in checks:
        if any(word in text for word in words):
            return subject
    return ("中枢官署、官员与案牍", "officials" if kind == "institution" else "ritual")


def render(item: dict, kind: str, introduction: str) -> Image.Image:
    seed = f"{kind}:{item['id']}:{item.get('name', '')}:{item.get('category', '')}"
    name = item.get("name", "")
    category = item.get("category", "")
    subject, scene = visual_subject(item, kind, introduction)
    base_by_scene = {
        "astronomy": STYLE_SCHOLAR,
        "officials": STYLE_REFERENCE,
        "commerce": STYLE_LOCAL,
        "ritual": STYLE_RITUAL,
        "artifact": STYLE_ARTIFACT,
        "weapon": STYLE_MILITARY,
        "cannon": STYLE_MILITARY,
        "wall": STYLE_LOCAL,
        "tomb": STYLE_TOMB,
        "palace": STYLE_REFERENCE,
        "architecture": STYLE_SCHOLAR,
    }
    base_path = STYLE_TOMB if kind == "special" and category == "宫陵" else base_by_scene.get(scene, STYLE_REFERENCE)
    if not base_path.is_file():
        base_path = STYLE_REFERENCE
    image = parchment(seed, base_path)
    draw = ImageDraw.Draw(image, "RGBA")
    # 只保留轻量统一画框；叙事主体交给逐类的 AI 场景，防止覆盖画面内容。
    draw.rounded_rectangle((18, 18, SIZE[0] - 18, SIZE[1] - 18), radius=14, outline=(166, 112, 43, 175), width=4)
    draw.line((42, SIZE[1] - 49, SIZE[0] - 42, SIZE[1] - 49), fill=color(seed + "bottom", 145, 205), width=3)
    return image.filter(ImageFilter.GaussianBlur(0.18))


def asset_name(kind: str, item_id: str) -> str:
    return f"world_{kind}_{item_id.replace('-', '_')}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    institution_sections = defaultdict(list)
    special_sections = defaultdict(list)
    for section in rows("institution_section"):
        institution_sections[section["institution_id"]].append(section)
    for section in rows("special_section"):
        special_sections[section["special_item_id"]].append(section)
    items = [(row, "institution") for row in rows("institution")] + [(row, "special") for row in rows("special_item")]
    expected = {asset_name(kind, row["id"]) for row, kind in items}
    for old in OUT.glob("world_*.xml"):
        if old.stem in expected:
            old.unlink()
    manifest: list[dict] = []
    for row, kind in items:
        name = asset_name(kind, row["id"])
        section_rows = institution_sections[row["id"]] if kind == "institution" else special_sections[row["id"]]
        introduction = " ".join([str(row.get("function") or row.get("description") or "")] + [str(section.get("content", "")) for section in section_rows[:2]])
        subject, scene = visual_subject(row, kind, introduction)
        render(row, kind, introduction).save(OUT / f"{name}.webp", "WEBP", quality=82, method=6)
        category = row.get("category", "")
        manifest.append({
            "asset": f"{name}.webp",
            "kind": kind,
            "item_id": row["id"],
            "name": row.get("name", ""),
            "category": category,
            "style": "宣纸底、工笔线描、淡彩的明代资料画",
            "visual_subject": subject,
            "scene": scene,
            "content_brief": introduction[:180],
            "prompt": f"明代历史资料画，主题为{row.get('name', '')}；画面主体：{subject}。结合条目事实：{introduction[:96]}。宣纸底、工笔线描、淡彩、写实构图；不含文字、现代标志与水印。",
            "width": SIZE[0],
            "height": SIZE[1],
            "format": "WEBP",
        })
    manifest_path = CONTENT / "world_asset_manifest.jsonl"
    manifest_path.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in manifest), encoding="utf-8")
    print(f"生成逐条 WebP 资料画 {len(items)} 个，规格 {SIZE[0]}×{SIZE[1]}")


if __name__ == "__main__":
    main()
