#!/usr/bin/env python3
"""导出尚无画像的人物及其批量生图提示词。

输出为 UTF-8 BOM CSV，可直接用 Excel、Numbers 或批量生图工具打开。提示词只使用
正式人物库已有的姓名、称号、类别和纪年；没有可靠相貌资料时明确要求历史合理的概括性
形象，避免虚构具体容貌。
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "backend" / "data" / "ming_history.sqlite3"
DEFAULT_OUTPUT = ROOT / "docs" / "missing-portrait-prompts.csv"

STYLE = (
    "明代人物绢本肖像，参考现有 portrait_zhangjuzheng.png、portrait_qinliangyu.png "
    "与 portrait_zhuyuanzhang.png：工笔线描与细密木刻肌理，暖褐色宣纸底，"
    "青黛、赭石、暗金的低饱和配色，庄重克制；竖幅 2:3，人物居中，脸部位于上半部，"
    "上方留出安全裁切空间，适合 Android 人物卡纵向裁切。"
)

NEGATIVE_PROMPT = (
    "不要现代服装、现代发型、摄影写实、欧美面孔、奇幻盔甲、夸张宫殿、"
    "战斗动作、兵器特写、文字、姓名题字、印章、水印、logo、边框、多人、"
    "错误朝代服饰、过度鲜艳配色。"
)


def resource_name(person_id: str) -> str:
    return f"portrait_{person_id.replace('-', '_')}.png"


def role_description(category: str, title: str) -> str:
    if category == "帝王":
        if "太子" in title:
            return "明代储君，着符合储君身份的礼服与冠饰，不使用龙袍"
        return "明代帝王，着符合皇帝身份的礼服与冠饰，纹样节制，不夸张陈设"
    if category == "内廷":
        if any(token in title for token in ("皇后", "太后", "妃", "嫔", "夫人", "选侍", "公主", "郡主")):
            return "明代宫廷女性，着与正式称号相称的礼服、发饰与首饰，端庄静坐"
        if any(token in title for token in ("太监", "宦官", "中官", "司礼监")):
            return "明代宦官，着内廷常服或礼服，神情克制，不使用戏曲化妆容"
        return "明代内廷人物，服饰遵循称号所示身份，端庄半身肖像"
    if category == "宗藩":
        if any(token in title for token in ("公主", "郡主", "王妃")):
            return "明代宗室女性，着与封号相称的礼服与首饰，端庄半身肖像"
        return "明代宗室或藩王，着与封号相称的常服或礼服，避免僭用皇帝纹样"
    if category == "朝臣":
        return "明代文官，着与正式官职相称的官服与乌纱帽；补子、颜色与纹样不确定时从简"
    if category == "将帅":
        return "明代将帅，着合乎身份的布面甲、罩袍或武官常服，沉稳站姿或坐姿，不表现战斗场面"
    if category == "文苑":
        return "明代文人或学者，着素雅士人袍服，可配书卷、砚台或书架的淡雅背景"
    return "明代人物，服饰只依据正式称号作保守还原"


def prompt(row: sqlite3.Row) -> str:
    courtesy = f"，字或号为「{row['courtesy_name']}」" if row["courtesy_name"].strip() else ""
    years = row["years"].strip() or "生卒未详"
    return (
        f"为明代人物「{row['display_name']}」绘制单人历史肖像。正式称号：{row['title']}；"
        f"分类：{row['category']}；活动年号：{row['reign']}；生卒：{years}{courtesy}。"
        f"{role_description(row['category'], row['title'])}。"
        "若无传世肖像，不臆造可识别的真实面貌，采用符合明代身份、年龄不明时为成年人的概括性汉人形象。"
    )


def export(output: Path) -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"未找到内容库：{DATABASE}")
    with sqlite3.connect(DATABASE) as database:
        database.row_factory = sqlite3.Row
        people = database.execute(
            """
            SELECT id, name, display_name, title, category, reign, years, courtesy_name
            FROM person
            WHERE trim(COALESCE(portrait_key, '')) = ''
            ORDER BY archive_start_year, category, name
            """
        ).fetchall()

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "person_id",
                "人名",
                "分类",
                "正式称号",
                "活动年号",
                "生卒",
                "字或号",
                "建议资源文件名",
                "提示词",
                "风格",
                "负面提示词",
                "参考现有画像",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for person in people:
            writer.writerow(
                {
                    "person_id": person["id"],
                    "人名": person["display_name"],
                    "分类": person["category"],
                    "正式称号": person["title"],
                    "活动年号": person["reign"],
                    "生卒": person["years"],
                    "字或号": person["courtesy_name"],
                    "建议资源文件名": resource_name(person["id"]),
                    "提示词": prompt(person),
                    "风格": STYLE,
                    "负面提示词": NEGATIVE_PROMPT,
                    "参考现有画像": "portrait_zhangjuzheng.png；portrait_qinliangyu.png；portrait_zhuyuanzhang.png",
                }
            )
    return len(people)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出缺失人物画像的批量提示词 CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    count = export(arguments.output)
    print(f"已导出 {count} 位缺图人物：{arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
