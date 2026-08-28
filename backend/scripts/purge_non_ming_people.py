#!/usr/bin/env python3
"""删除内容库中混入的清朝与现代人物词条。

导入维基数据与百度百科时，同名检索曾把清代人物、现代人乃至神话人物
写入 person 表。本应用只收录明朝（含南明）人物，此处按人工甄别的名单
统一删除，并清理其关联的关系、栏目与研究记录。

判定口径：
- qing        主要历史身份为清朝人物（清朝将领、总督、三藩、旗人、清代左都御史等）；
- modern      词条内容实为现代同名人物（ Wikidata 同名匹配错撞，如歌手、教授、院士）；
- other       非明朝的朝代或非历史人物（唐朝宗室、《西游记》太白金星）。

例外：lifangying（李芳英）确为李文忠第三子，仅简介被现代同名者资料污染，
本脚本改写其简介而不删除。
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

PURGE_LIST: dict[str, tuple[str, str]] = {
    # ---- 清朝人物 ----
    "caiyurong": ("qing", "蔡毓荣，汉军正白旗，清朝云贵总督"),
    "kongsizhen": ("qing", "孔四贞，清朝唯一的汉族公主"),
    "kongyoude": ("qing", "孔有德，降清封定南王"),
    "shangkexi": ("qing", "尚可喜，降清封平南王"),
    "shangzhixin": ("qing", "尚之信，三藩之乱清方藩王"),
    "shangzhixiao": ("qing", "尚之孝，平南王之子，汉军镶蓝旗"),
    "gengzhongming": ("qing", "耿仲明，降清封靖南王"),
    "gengjimao": ("qing", "耿继茂，清靖南王"),
    "gengjingzhong": ("qing", "耿精忠，清朝靖南王"),
    "gengzhaozhong": ("qing", "耿昭忠，汉军正黄旗"),
    "wuxingzuo": ("qing", "吴兴祚，入汉军正红旗，清朝两广总督"),
    "wanzhengse": ("qing", "万正色，清朝水师提督"),
    "shilang": ("qing", "施琅，清朝福建水师提督"),
    "sunyanling": ("qing", "孙延龄，汉军正红旗，清藩"),
    "sunsike": ("qing", "孙思克，清朝名将，河西四汉将"),
    "wangjinbao": ("qing", "王进宝，清朝名将，河西四汉将"),
    "langtingzuo": ("qing", "郎廷佐，汉军镶黄旗，清朝总督"),
    "lilvtai": ("qing", "李率泰，清初汉军正蓝旗"),
    "liufangming": ("qing", "刘芳名，汉军正白旗贰臣"),
    "liuwuyuan": ("qing", "刘武元，汉军镶红旗贰臣"),
    "zuzepu": ("qing", "祖泽溥，祖大寿长子，清朝总督"),
    "zuzerun": ("qing", "祖泽润，明末清初降清将领"),
    "yaoqisheng": ("qing", "姚启圣，清朝福建总督"),
    "mutianyan": ("qing", "慕天颜，清朝官员"),
    "maxiongzhen": ("qing", "马雄镇，汉军镶红旗，清朝广西巡抚"),
    "fuhonglie": ("qing", "傅弘烈，清朝广西巡抚"),
    "yuchenglong": ("qing", "于成龙，清朝初年名臣，仕途全在清"),
    "zhaoliangdong": ("qing", "赵良栋，清朝河西四将之一"),
    "zuzehong": ("qing", "祖泽洪，大凌河降清，汉军镶黄旗，清朝学士"),
    "zhuchun": ("qing", "朱椿，清代乾隆间左都御史（与明蜀献王同名）"),
    # ---- 现代同名人物（词条内容与明朝无关） ----
    "caoyuan": ("modern", "1955年生，中共党员"),
    "cuijingrong": ("modern", "华裔美国工程院院士"),
    "fanying": ("modern", "外交学院教授"),
    "guogong": ("modern", "1908—1998，满族现代人物"),
    "heqing": ("modern", "1986年生，主持人"),
    "hongzhong": ("modern", "中国香港男歌手"),
    "huangzongming": ("modern", "1957年生，高校校长"),
    "leianmin": ("modern", "1970年生，研究员"),
    "lichengxun": ("modern", "韩国速度滑冰运动员"),
    "lifangying_moved": ("modern", "占位，避免下标错误"),
    "liqiao": ("modern", "西南交通大学教授"),
    "liushuzu": ("modern", "现代学者、发明家"),
    "liuyu": ("modern", "1968年生，企业董事长"),
    "luguangzu": ("modern", "羽毛球运动员"),
    "sunjie": ("modern", "1986年生，篮球运动员"),
    "sunwei": ("modern", "1975年生，影视演员"),
    "tanglong": ("modern", "韩国动作演员"),
    "tianxiong": ("modern", "1946年生，企业家"),
    "wangguoan": ("modern", "韩后品牌创始人"),
    "wangjiceng": ("modern", "清末民初外交官"),
    "wangjing": ("modern", "医学副教授"),
    "wangjun": ("modern", "影视导演"),
    "xiongrulin": ("modern", "1978年生，歌手"),
    "xuben": ("modern", "1950年生，美国高校教授"),
    "xuke": ("modern", "1974年生，清华大学教授"),
    "yangbo": ("modern", "1968年生，党校研究生"),
    "yanggeng": ("modern", "1939年生，画家"),
    "yangwei": ("modern", "上海中医药大学医生"),
    "zhangchao": ("modern", "1956年生，演员"),
    "zhangchun": ("modern", "1983年生，动画导演"),
    "zhangjie": ("modern", "1982年生，流行歌手"),
    "zhangtianfu": ("modern", "1910—2017，茶学家"),
    "zhangtianlu": ("modern", "1926年生，药学编辑"),
    "zhangyu2": ("modern", "1969年生，央视主持人"),
    "zhangyue": ("modern", "1980年生，摄影师"),
    "zhaomenglin": ("modern", "射击运动员"),
    "zhengding": ("modern", "1963—2007，法学家"),
    "zhengxiao": ("modern", "越剧演员"),
    "zhouxuan2": ("modern", "加拿大协会执行主席"),
    "zhumei": ("modern", "现代歌手家属"),
    # ---- 其他朝代 / 非历史人物 ----
    "liqing": ("other", "唐朝宗室李琩（初名李清）"),
    "lichanggeng": ("other", "《西游记》太白金星，神话人物"),
}
# lifangying 不删除：确为李文忠第三子，仅改写被污染的简介。
PURGE_LIST.pop("lifangying_moved", None)

LIFANGYING_BIO = "李芳英，李文忠第三子，官至中都正留守。"


def purge(db: sqlite3.Connection) -> None:
    ids = sorted(PURGE_LIST)
    marks = ",".join("?" * len(ids))
    removed_relations = db.execute(
        f"DELETE FROM person_relation WHERE from_person_id IN ({marks}) OR to_person_id IN ({marks})",
        ids + ids,
    ).rowcount
    removed_sections = db.execute(
        f"DELETE FROM person_section WHERE person_id IN ({marks})", ids
    ).rowcount
    removed_research = db.execute(
        f"DELETE FROM person_research WHERE person_id IN ({marks})", ids
    ).rowcount
    removed_references = db.execute(
        f"DELETE FROM content_reference WHERE content_type = 'person' AND content_id IN ({marks})",
        ids,
    ).rowcount
    removed_people = db.execute(f"DELETE FROM person WHERE id IN ({marks})", ids).rowcount
    db.execute("UPDATE person SET summary = ?, biography = ? WHERE id = 'lifangying'", (LIFANGYING_BIO, LIFANGYING_BIO))
    print(
        f"人物 {removed_people} 条；关系 {removed_relations} 条；栏目 {removed_sections} 条；"
        f"研究记录 {removed_research} 条；资料出处 {removed_references} 条。"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="删除混入内容库的清朝与现代人物词条")
    parser.add_argument("--dry-run", action="store_true", help="只打印将删除的名单，不写入数据库")
    args = parser.parse_args()

    if args.dry_run:
        for person_id, (kind, reason) in sorted(PURGE_LIST.items()):
            print(f"{person_id}\t{kind}\t{reason}")
        return 0

    database_path = BACKEND_DIRECTORY / "data" / "ming_history.sqlite3"
    with sqlite3.connect(database_path) as db:
        purge(db)
    print("李芳英简介已改写为明朝史料表述。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
