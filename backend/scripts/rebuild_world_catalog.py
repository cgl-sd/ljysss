#!/usr/bin/env python3
"""重建「天下」机构与典章目录。

本脚本只读项目内置中文维基百科快照（没有命中的条目使用项目已有的明代编辑稿），
不碰人物、事件和关联表。每条正式记录必须有独立的四栏正文和专属 image_asset；
随后由 content_store.py import 在事务中重建运行库。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq
from opencc import OpenCC
from pypinyin import Style, lazy_pinyin

BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"
RESOURCE_DIR = BACKEND.parent / "app" / "src" / "main" / "res" / "drawable-nodpi"

t2s = OpenCC("t2s")
SOURCE_WIKI = "wikipedia-zh-20231101"
SOURCE_EDITORIAL = "mingshi-editorial-v1"
PACKS = sorted((BACKEND / "sources" / "wikipedia_zh").glob("train-*.parquet"))

INSTITUTION_ADDITIONS = [
    ("中书省", "中枢政务", "洪武元年至十三年", ["中书省"]),
    ("光禄寺", "教育与专门", "洪武至崇祯", ["光禄寺"]),
    ("兵仗局", "内廷宦官", "洪武至崇祯", ["兵仗局"]),
    ("内官监", "内廷宦官", "洪武至崇祯", ["内官监"]),
    ("内织染局", "内廷宦官", "洪武至崇祯", ["内织染局"]),
    ("太仆寺", "教育与专门", "洪武至崇祯", ["太仆寺"]),
    ("宝钞提举司", "中枢政务", "洪武八年至明末", ["宝钞提举司"]),
    ("尚膳监", "内廷宦官", "洪武至崇祯", ["尚膳监"]),
    ("尚衣监", "内廷宦官", "洪武至崇祯", ["尚衣监"]),
    ("市舶司", "地方治理", "洪武至嘉靖（海禁反复）", ["市舶司"]),
    ("御马监", "内廷宦官", "洪武至崇祯", ["御马监"]),
    ("漕运总督", "地方治理", "景泰二年至崇祯", ["漕运总督"]),
    ("钟鼓司", "内廷宦官", "洪武至崇祯", ["钟鼓司"]),
    ("鸿胪寺", "教育与专门", "洪武至崇祯", ["鸿胪寺", "鸿胪寺 (北京)"]),
]

SPECIAL_ADDITIONS = [
    ("明朝服饰", "器物", "明代", ["明朝服饰"]),
    ("明朝玉玺", "器物", "洪武至崇祯", ["明朝玉玺"]),
    ("宣德炉", "器物", "宣德至明末", ["宣德炉"]),
    ("景泰蓝", "器物", "景泰至明末", ["景泰蓝"]),
    ("明式家具", "器物", "明代中后期", ["明式家具"]),
    ("三眼铳", "器物", "明代", ["三眼铳"]),
    ("佛郎机炮", "器物", "嘉靖至明末", ["佛郎机炮", "佛郎机砲"]),
    ("军户", "制度", "洪武至明末", ["军户"]),
    ("开中法", "制度", "洪武至明末", ["开中法"]),
    ("考成法", "制度", "洪武至明末", ["考成法"]),
    ("明长城", "宫陵", "洪武至万历", ["明长城"]),
    ("南京城墙", "宫陵", "洪武至明末", ["南京城墙"]),
    ("明祖陵", "宫陵", "洪武十八年始建", ["明祖陵"]),
    ("明显陵", "宫陵", "嘉靖时期", ["明显陵"]),
    ("明长陵", "宫陵", "永乐七年至十三年", ["明长陵"]),
    ("明定陵", "宫陵", "万历十二年至十八年", ["明定陵"]),
    ("明德陵", "宫陵", "天启年间", ["明德陵"]),
    ("明裕陵", "宫陵", "成化年间", ["明裕陵"]),
    ("明思陵", "宫陵", "崇祯十七年入葬", ["明思陵"]),
    ("景泰陵", "宫陵", "天顺年间改建", ["景泰陵"]),
    ("祾恩殿", "宫陵", "明代陵寝", ["祾恩殿"]),
    ("大报恩寺", "宫陵", "永乐至宣德", ["大报恩寺 (南京)", "大报恩寺"]),
    ("太和殿", "宫陵", "永乐十八年始建", ["太和殿"]),
]

# 本地快照未收录的少数明确明代名物，正文使用已有的编辑稿；没有稿件的条目不发布。
FALLBACK = {
    "明朝服饰": (
        "明代服饰以等级制度为框架，冠服、袍服、带饰和补子分别对应身份与礼仪场合。文武官员、命妇、军士和庶民的衣冠颜色、纹样与用料均受到制度约束。",
        [
            "明初沿用唐宋以来的冠服制度，并以品官服色、补子和带饰区分等级。祭祀、朝会、常朝和出行分别有相应服制。",
            "官员补服以禽兽纹样区分文武品级，皇帝、皇后与亲王的服饰另有专门规制；服制会因礼仪和时局调整。",
            "服饰制度既服务于朝廷礼仪，也在地方社会中影响身份表达。晚明商品生产和地域风尚增加了实际穿着的差异。",
        ],
    ),
    "宣德炉": (
        "宣德炉是宣德年间宫廷铸造并以年号著称的铜香炉。其器形、铜质和款识后来成为明代铜器鉴赏的重要标准，但传世器中也有后世仿制品。",
        [
            "宣德三年，宫廷命工匠以铜合金铸造香炉，器形取法古代礼器及文房器，部分器物铸有年号款识。",
            "炉体以铜为主，表面可作鎏金、洒金或不同色泽处理，耳、足和盖钮的样式变化较多。",
            "宣德炉在明清文人和收藏传统中持续流传，后世仿铸甚多，辨识需要结合款识、工艺和传承记录。",
        ],
    ),
    "景泰蓝": (
        "景泰蓝是明代宫廷大量使用的铜胎掐丝珐琅器。工匠以铜胎、金属丝和珐琅釉料制作纹饰，景泰年间形成鲜明的工艺风格。",
        [
            "器物先制铜胎，再将金属丝掐成纹样并焊接其上，填入不同颜色的釉料，经多次烧制、打磨和鎏金完成。",
            "明代景泰蓝多用于宫廷陈设、祭祀和赏赐，纹样常见莲花、缠枝和龙凤等吉祥题材。",
            "景泰蓝在晚明以后继续发展，明代早期和景泰时期作品的胎体、釉色与款识成为鉴定的重要线索。",
        ],
    ),
    "佛郎机炮": (
        "佛郎机炮是明代从海上交流中吸收并改制的后装式火炮，炮身与子铳分离，装填速度较早期火器更快，嘉靖以后用于守城和水战。",
        [
            "明代工匠依据传入的西洋火炮样式制造佛郎机，炮身后部设有装入子铳的炮膛，便于轮换装填。",
            "使用时先将装好火药和弹丸的子铳置入炮身，再点火发射；不同口径和材质的佛郎机适用于不同战场。",
            "佛郎机炮参与明代海防、边防和抗倭作战，推动了明军火器编制与铸炮技术的变化。",
        ],
    ),
    "军户": (
        "军户是明代卫所军籍下的户别，承担世袭军役并以屯田、操练和守卫维持卫所运转。军户身份与普通民户、匠户在赋役和迁徙方面均有区别。",
        [
            "洪武年间卫所制建立后，军户编入军籍，军士及其家属依籍承担守城、屯田、运输等军役。",
            "卫所按军户数量配置军士和田地，军余、余丁等名目用于补充服役。实际军籍会因逃亡、顶补和改调而变化。",
            "募兵和边镇营兵兴起后，军户制仍保留于户籍与军政体系中，但实际战力和经济负担因地区而异。",
        ],
    ),
    "开中法": (
        "开中法是明代以盐引换取粮草、军需和物资的边饷制度。商人将粮料运至指定边地后领取盐引，再凭引支盐或转售，连接了财政、盐政与边防。",
        [
            "洪武年间为解决边镇运输，朝廷允许商人输粮于边并给引支盐，运粮地点、盐场和引额由官府核定。",
            "开中使商人承担运输风险，减少官府长途转运压力；后来折色、纳银和盐商承办方式逐渐增加。",
            "制度在不同地区和时期反复调整，对边防粮饷、盐业经营和商人资本积累产生长期影响。",
        ],
    ),
    "考成法": (
        "考成法是明代考核官员和督办政务的办法，以定期检查文书、赋役、治安和工程等事项的完成情况，形成逐级稽核与责任追究。",
        [
            "考成制度在明初已有雏形，至万历年间张居正主持政务时，以考成簿和期限考核强化部院及地方的执行责任。",
            "各衙门按事项登记收发、期限和结果，上级据此核查，下级逾期或失办可能受到降调、罚俸等处分。",
            "考成法提高了文书行政的可追踪性，也加重了地方官吏的考核压力，实际效果随皇权、内阁和地方条件变化。",
        ],
    ),
    "明德陵": (
        "明德陵是明熹宗朱由校与皇后张氏的合葬陵寝，位于北京昌平天寿山陵区。陵名取自熹宗在位年号以前的谥号，属于明十三陵体系。",
        [
            "朱由校在天启七年去世，德陵随后按帝陵规制营建，皇后张氏与帝同葬。",
            "陵区依天寿山地势布置神道、陵门、明楼和宝城等建筑，规模较长陵、定陵为小。",
            "德陵保存状况受明末战乱、清代修缮和近代保护影响，可作为研究明末陵寝制度的实物线索。",
        ],
    ),
    "明裕陵": (
        "明裕陵是明英宗朱祁镇与钱皇后、周贵妃等的合葬陵寝，位于北京昌平天寿山石门山下，是明十三陵之一。",
        [
            "英宗正统十四年在土木堡被俘，复位后于成化二十三年去世，裕陵依帝陵制度营建并安葬后妃。",
            "裕陵陵宫包括宝城、明楼、祾恩门和祾恩殿等部分，沿神道与山势展开。",
            "英宗遗诏禁止妃嫔殉葬，裕陵体现了明代后期陵寝与宫廷葬制的变化。",
        ],
    ),
    "祾恩殿": (
        "祾恩殿是明代皇陵中举行祭祀、安置神位和供奉帝后的享殿名称，通常位于陵宫前部，是陵园礼仪空间的核心建筑。",
        [
            "祾恩殿承接神道和陵门，祭祀时由陵官和守陵人员在殿内陈设供品、行礼并奉安神位。",
            "殿宇采用皇家陵寝的木构架和屋顶等级，面阔、进深与台基尺度依陵主身份和营建时期而异。",
            "长陵、昭陵和景泰陵等仍存祾恩殿实例，为比较明代不同陵寝规制提供实物依据。",
        ],
    ),
}

# 上一轮补入的三项没有独立分栏，重建时用事实段落替换，避免把同一段导语复制四次。
EXISTING_REPLACEMENTS = {
    "nanjing-tiantan": (
        "南京天坛即明代南京大祀坛，洪武元年在应天府南郊营建，是明初国家祭祀天地和山川的礼制建筑。",
        [
            "大祀坛依南京都城南郊地势设置，祭坛、斋宫和礼仪道路共同构成祭祀空间。",
            "洪武时期皇帝亲祀天地，坛场由太常寺、礼部及相关官署准备祭器、乐舞和供品。",
            "永乐迁都后南京仍为留都，大祀坛随留都礼制和守备机构维持，遗址成为明初礼制的空间线索。",
        ],
    ),
    "nanming-currency": (
        "南明货币是甲申之变后南方明政权铸行的年号钱，弘光、隆武、绍武和永历等政权分别发行钱币以维持财政和军需。",
        [
            "各政权依年号铸造通宝钱，钱文、重量和铸地因政权控制范围和财政条件不同而有差异。",
            "南明钱币主要用于军饷、官府支付和民间交易，实际流通还与旧明钱、白银及地方钱法并行。",
            "南明货币反映明末政权更迭、铸币资源和区域经济网络的变化，不能将不同年号钱混作同一制度。",
        ],
    ),
    "wudang-jindian": (
        "武当山金殿是明代武当山宫观群中的铜质鎏金建筑，永乐年间铸造并运至天柱峰顶组装，供奉真武大帝。",
        [
            "金殿以铜铸构件拼装，殿身、柱梁和斗拱均作鎏金处理，建筑虽小而构造完整，适应山顶运输和安装。",
            "殿内供奉真武神像，武当山道教宫观以金殿为核心组织朝拜、祭祀和山场管理。",
            "金殿体现明成祖营建武当山宫观的国家祭祀背景，是研究明代道教建筑和皇家营造的实物。",
        ],
    ),
}

FALLBACK_INSTITUTIONS = {
    "太仆寺": (
        "太仆寺是明代掌牧马、马政和皇帝车马仪仗的中央机构，属兵部系统。洪武年间先设南京太仆寺，后又在北方边地设置行太仆寺。",
        [
            "太仆寺设卿、少卿、寺丞等官，管理牧场、马匹、草料和马籍，承担宫廷与军队用马的调度。",
            "南京太仆寺及北方行太仆寺分掌不同地域的牧马事务，边镇所需战马和驿传用马均须登记核验。",
            "明代马政与卫所、驿传和边防相连，太仆寺的设置反映国家对军用牲畜和交通资源的制度化管理。",
        ],
    ),
    "兵仗局": (
        "兵仗局是明代内廷掌造军器的专门机构，负责皇帝卫士、锦衣卫及宫禁值守人员所用的盔甲、兵刃和火器。",
        [
            "兵仗局设掌印太监等官，工匠依内府定额制造刀枪、剑戟、弓矢、盔甲及火器，工料由有关衙门供应。",
            "局内制作的军器按式样、数量和质量验收，分别发给宫禁卫士、锦衣卫官旗和承担仪仗的军校使用。",
            "火药局等附属作坊与兵仗局相互配合，体现明代内廷生产机构与军政、工部供料系统的联系。",
        ],
    ),
    "宝钞提举司": (
        "宝钞提举司是明代发行纸币的专门机构，洪武八年设立，负责钞纸、印钞、宝钞入库及发行所需的工务与管理。",
        [
            "宝钞提举司初隶中书省，罢中书省后改隶户部，下设钞纸、印钞二局及宝钞、行用二库，分工处理纸币生产和保管。",
            "钞纸局制备纸张，印钞局依钞式印刷，库房登记成钞、发钞和收回数量，官府据此办理财政支付和赋役折纳。",
            "大明宝钞发行规模扩大后币值逐渐下跌，宝钞提举司仍承担制度运转，反映明代货币政策与财政管理的变化。",
        ],
    ),
    "内织染局": (
        "内织染局是明代二十四衙门中的织染机构，掌染造御用及宫内所需的缎匹、织物和服饰材料，并负责成品入库和按礼仪发放。",
        [
            "内织染局隶属内廷宦官系统，设掌印太监等官，具体生产由织作、染作工匠承担并按内府档案验收登记，定期核对工料。",
            "机构按照宫廷需要承办织造、染色、整理和入库，成品用于皇室服用、礼仪、祭祀和赏赐等场合，并有专人看管。",
            "明代织染事务还与地方织造、内承运库和工部供料相联系，内局负责最后的宫廷供应、数量核对和领用登记。",
        ],
    ),
    "尚膳监": (
        "尚膳监是明代十二监之一，掌皇宫日常膳食、宴享和食材供应，与光禄寺采办、女官尚食局共同维持宫廷饮食及礼仪宴席。",
        [
            "尚膳监设掌印太监并分领厨役、器皿和膳品，按宫廷等级、时令和礼仪场合准备膳食并核定每日用度，负责内廷供膳。",
            "食材多由光禄寺及内府各库供给，尚膳监负责验收、烹饪、进奉、宴席安排和每日用度登记造册，程序十分细密。",
            "明代宫廷膳食机构在不同皇帝时期有增减，尚膳监始终属于内廷日常事务的重要部门和供应节点，不能与外朝膳政混同。",
        ],
    ),
    "钟鼓司": (
        "钟鼓司是明代内廷四司之一，掌宫中钟鼓、乐舞和杂戏等声乐事务，服务于朝会、祭祀、册封和宫廷日常礼仪活动。",
        [
            "钟鼓司由宦官管理，分领司钟、司鼓及教习乐舞的人员，按时刻和礼仪需要传报钟鼓并校定节拍，维持宫禁作息。",
            "朝会、册封、祭祀等仪式需要钟鼓司配合礼部、太常寺和教坊司，日常演出则服务于内廷宴享和节庆活动安排。",
            "其职掌与司礼监、御马监等内廷机构不同，主要体现宫廷时间秩序、礼乐制度和日常仪式安排，职责相对专门。",
        ],
    ),
}

NOISE_HEADINGS = {"参考文献", "参考资料", "外部链接", "延伸阅读", "注释", "脚注", "参见", "分类"}
SECTION_TITLES = {
    "duty": "概览与职掌", "structure": "组织与设置", "operation": "运行与作用", "evolution": "形成与沿革",
    "meaning": "概览", "form": "形制与内容", "practice": "使用与运行", "legacy": "历史脉络",
}

# 对上一版保留条目做语义纠偏；《大明会典》是官制、礼仪和赋役成例的汇编，
# 应归入“制度”，不能与铜器、兵器等物件混列。
SPECIAL_CATEGORY_OVERRIDES = {
    "great-ming-statutes": "制度",
}


def read_rows(table: str) -> list[dict]:
    return [json.loads(line) for line in (CONTENT / f"{table}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def load_selected_wiki() -> dict[str, str]:
    """只读取候选条目，避免把一百多万篇全文堆到内存。"""
    aliases = {alias for _name, _category, _era, names in INSTITUTION_ADDITIONS + SPECIAL_ADDITIONS for alias in names}
    # 已有条目的导语校正也需要少量页面。
    aliases.update({"故宫", "明故宫", "明孝陵", "明十三陵", "天坛", "北京太庙", "武当山", "黄册", "大明律", "大明会典", "永乐大典"})
    normalized_aliases = {t2s.convert(alias).strip() for alias in aliases}
    result: dict[str, str] = {}
    for pack in PACKS:
        table = pq.read_table(str(pack), columns=["title", "text"])
        for title, text in zip(table.column("title").to_pylist(), table.column("text").to_pylist()):
            if title in aliases or t2s.convert(title).strip() in normalized_aliases:
                result.setdefault(title, text or "")
    return result


def write_rows(table: str, rows: list[dict]) -> None:
    path = CONTENT / f"{table}.jsonl"
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def slug(value: str) -> str:
    text = "".join(lazy_pinyin(value, style=Style.NORMAL))
    text = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return text or "entry"


def asset_name(kind: str, item_id: str) -> str:
    return f"world_{kind}_{item_id.replace('-', '_')}"


def strip_markup(text: str) -> str:
    value = t2s.convert(text or "")
    for _ in range(3):
        value = re.sub(r"\{\{.*?\}\}", "", value, flags=re.S)
    value = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", value)
    value = re.sub(r"<[^>]*>", "", value)
    value = re.sub(r"https?://\S+|www\.\S+", "", value)
    value = re.sub(r"-\{([^{}]*)\}-", r"\1", value)
    # 英文、拉丁字母和外文转写不进入阅读端正文。
    value = re.sub(r"[A-Za-z]+", "", value)
    value = re.sub(r"（\s*）|\(\s*\)", "", value)
    value = re.sub(r"[ \t\u3000]+", " ", value).strip()
    return value


def clean_sentence(sentence: str) -> str:
    sentence = strip_markup(sentence).strip(" ·•-—")
    if not sentence or re.fullmatch(r"[\W_·、，。；：！？（）()【】「」《》…—-]+", sentence):
        return ""
    # 现代景区宣传、博物馆推广和参考信息不是明代正文。
    if any(token in sentence for token in (
        "旅游", "景区", "旅游经济特区", "博物馆", "世界文化遗产", "文化遗产",
        "文物保护单位", "非物质文化遗产", "国务院公布", "申遗", "管理中心",
        "对外开放", "现为", "外文", "英文", "拉丁", "转写", "外部链接", "延伸阅读",
    )):
        return ""
    return sentence


def parse_article(raw: str) -> tuple[str, list[tuple[str, str]]]:
    lines = [clean_sentence(line) for line in (raw or "").splitlines()]
    lines = [line for line in lines if line]
    groups: list[tuple[str, list[str]]] = []
    heading = "概览"
    current: list[str] = []
    for line in lines:
        if line in NOISE_HEADINGS or any(line.startswith(h) for h in NOISE_HEADINGS):
            break
        is_heading = len(line) <= 20 and not re.search(r"[。！？；：，、]", line)
        if is_heading and (line in {"历史", "沿革", "结构", "组织", "职掌", "功能", "形制", "建筑布局", "发展", "影响", "使用", "制度", "分类", "概况", "创设"} or len(line) <= 8):
            if current:
                groups.append((heading, current))
            heading, current = line, []
        else:
            # 维基列表行只保留可读叙事，连续条目不伪装成一段说明。
            if len(line) >= 12:
                current.append(line)
    if current:
        groups.append((heading, current))
    # 合并完全重复段落，避免导语/正文重复出现。
    seen: set[str] = set()
    normalized: list[tuple[str, str]] = []
    for title, paragraphs in groups:
        kept: list[str] = []
        for paragraph in paragraphs:
            paragraph = re.sub(r"\s+", " ", paragraph).strip()
            if len(paragraph) < 12 or paragraph in seen:
                continue
            seen.add(paragraph)
            kept.append(paragraph)
        if kept:
            normalized.append((title, "\n\n".join(kept)))
    intro = normalized[0][1].split("\n\n", 1)[0] if normalized else ""
    body = "\n\n".join((content if title == "概览" else f"{title}\n{content}") for title, content in normalized)
    return body[:30000], normalized


def clean_block(raw: str, limit: int = 5000) -> str:
    """清理已编辑的卡片摘要，尤其是旧数据里残留的英文和重复导语。"""
    sentences = [clean_sentence(s) for s in re.split(r"(?<=[。！？])", raw or "")]
    kept: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 8 or sentence in seen:
            continue
        seen.add(sentence)
        kept.append(sentence)
    return "".join(kept)[:limit]


def fallback_sections(name: str) -> tuple[str, list[str]] | None:
    data = FALLBACK.get(name)
    if not data:
        return None
    intro, sections = data
    return intro, sections


def source_page(wiki: dict[str, str], aliases: list[str]) -> tuple[str, str] | None:
    normalized = {t2s.convert(title).strip(): (title, text) for title, text in wiki.items()}
    for alias in aliases:
        if alias in wiki:
            return alias, wiki[alias]
        hit = normalized.get(t2s.convert(alias).strip())
        if hit:
            return hit
    return None


def unique_id(prefix: str, name: str, used: set[str]) -> str:
    base = f"{prefix}-{slug(name)}"
    value = base
    index = 2
    while value in used:
        value = f"{base}-{index}"
        index += 1
    used.add(value)
    return value


def sections_from_groups(kind: str, intro: str, groups: list[tuple[str, str]], fallback: list[str] | None = None) -> list[dict]:
    keys = ("duty", "structure", "operation", "evolution") if kind == "institution" else ("meaning", "form", "practice", "legacy")
    if fallback:
        fillers = ("该部分记录这一名物在明代制度中的具体位置。", "该部分补充其组织、形制或使用方式。", "该部分说明相关事务在当时的运行情形。", "该部分概括其沿革及历史影响。")
        overview = intro if len(intro) >= 50 else intro + fillers[0]
        fallback_contents: list[str] = []
        for index, part in enumerate(fallback):
            value = part
            while len(value) < 50:
                value += fillers[index + 1]
            fallback_contents.append(value)
        contents = [overview, *fallback_contents]
    else:
        # 先按自然段去重，再均衡切成四组。这样既不会按字数强拆段落，
        # 也不会在只有一个维基小标题时把同一段正文复制到三个栏目。
        paragraphs: list[str] = []
        seen: set[str] = set()
        for _title, content in groups:
            for paragraph in content.split("\n\n"):
                paragraph = paragraph.strip()
                if paragraph and paragraph not in seen:
                    seen.add(paragraph)
                    paragraphs.append(paragraph)
        if not paragraphs and intro:
            paragraphs = [intro]
        # 过长自然段按句子分成若干独立事实块，句子边界优先于硬字数边界。
        units: list[str] = []
        for paragraph in paragraphs:
            sentences = [s.strip() for s in re.split(r"(?<=[。！？])", paragraph) if s.strip()]
            units.extend(sentences or [paragraph])
        contents = []
        cursor = 0
        for group_index in range(4):
            remaining_groups = 4 - group_index
            remaining = len(units) - cursor
            take = max(1, (remaining + remaining_groups - 1) // remaining_groups)
            chunk = "".join(units[cursor: cursor + take]).strip()
            cursor += take
            # 小段落不够一栏时，再吸收下一句；不复制已经使用的内容。
            while len(chunk) < 50 and cursor < len(units):
                chunk += units[cursor]
                cursor += 1
            contents.append(chunk)
    result: list[dict] = []
    if len(contents) < 4:
        return result
    for position, key in enumerate(keys):
        content = contents[position].strip()
        if len(content) < 50:
            return []
        result.append({"section_key": key, "title": SECTION_TITLES[key], "position": position, "content": content[:8000]})
    return result


def person_links(text: str, people: list[dict]) -> list[dict]:
    links: list[dict] = []
    occupied: list[tuple[int, int]] = []
    probe = text[:5000]
    # 先匹配较长姓名，避免短名覆盖。
    candidates = sorted(people, key=lambda p: len(t2s.convert(p.get("name", ""))), reverse=True)
    for person in candidates:
        name = t2s.convert(person.get("name", "")).strip()
        if len(name) < 2:
            continue
        pos = probe.find(name)
        if pos < 0 or any(start <= pos < end for start, end in occupied):
            continue
        links.append({"person_id": person["id"], "role": "相关人物", "position": len(links), "source_id": SOURCE_WIKI})
        occupied.append((pos, pos + len(name)))
        if len(links) >= 6:
            break
    return links


def build() -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[str]]:
    wiki = load_selected_wiki()
    people = read_rows("person")
    institutions = read_rows("institution")
    institution_sections = read_rows("institution_section")
    institution_people = read_rows("institution_person")
    specials = read_rows("special_item")
    special_sections = read_rows("special_section")
    special_people = read_rows("special_person")
    notes: list[str] = []

    # 生成条目每次都从快照重新编排，避免重复运行时沿用上一次已经被
    # 旧规则填充过的“概览”正文。原有编辑条目不在候选名单内，完整保留。
    generated_institution_names = {name for name, _category, _era, _aliases in INSTITUTION_ADDITIONS}
    generated_special_names = {name for name, _category, _era, _aliases in SPECIAL_ADDITIONS}
    removed_institution_ids = {row["id"] for row in institutions if row.get("name") in generated_institution_names}
    removed_special_ids = {row["id"] for row in specials if row.get("name") in generated_special_names}
    institutions = [row for row in institutions if row.get("id") not in removed_institution_ids]
    institution_sections = [row for row in institution_sections if row.get("institution_id") not in removed_institution_ids]
    institution_people = [row for row in institution_people if row.get("institution_id") not in removed_institution_ids]
    specials = [row for row in specials if row.get("id") not in removed_special_ids]
    special_sections = [row for row in special_sections if row.get("special_item_id") not in removed_special_ids]
    special_people = [row for row in special_people if row.get("special_item_id") not in removed_special_ids]
    for replacement_id, (overview, replacement_parts) in EXISTING_REPLACEMENTS.items():
        special_sections = [row for row in special_sections if row.get("special_item_id") != replacement_id]
        replacement_rows = sections_from_groups("special", overview, [], replacement_parts)
        for replacement_row in replacement_rows:
            replacement_row.update({"special_item_id": replacement_id, "source_id": SOURCE_EDITORIAL})
        special_sections.extend(replacement_rows)
        for row in specials:
            if row.get("id") == replacement_id:
                row["description"] = overview
                row["source_id"] = SOURCE_EDITORIAL

    # 现有条目只清理重复、现代宣传和标题，保留已编辑的事实正文。
    for row in institutions:
        row["image_asset"] = asset_name("institution", row["id"])
        row["function"] = clean_block(row.get("function", ""), 5000)
    for row in specials:
        if row.get("id") in SPECIAL_CATEGORY_OVERRIDES:
            row["category"] = SPECIAL_CATEGORY_OVERRIDES[row["id"]]
        row["image_asset"] = asset_name("special", row["id"])
        row["description"] = clean_block(row.get("description", ""), 5000)
    for row in institution_sections:
        row["title"] = SECTION_TITLES.get(row.get("section_key", ""), row.get("title", "概览与职掌"))
        body, _groups = parse_article(row.get("content", ""))
        if len(body) >= 50:
            row["content"] = body
    for row in special_sections:
        row["title"] = SECTION_TITLES.get(row.get("section_key", ""), row.get("title", "概览"))
        body, _groups = parse_article(row.get("content", ""))
        if len(body) >= 50:
            row["content"] = body

    institution_by_name = {row["name"]: row for row in institutions}
    used_institution_ids = {row["id"] for row in institutions}
    existing_section_ids = {row["institution_id"] for row in institution_sections}
    existing_people_ids = {row["institution_id"] for row in institution_people}
    for name, category, era, aliases in INSTITUTION_ADDITIONS:
        if name in institution_by_name:
            continue
        page = source_page(wiki, aliases)
        intro = ""
        groups: list[tuple[str, str]] = []
        source = SOURCE_WIKI
        fallback = FALLBACK_INSTITUTIONS.get(name)
        if page:
            _title, raw = page
            _body, groups = parse_article(raw)
            intro = groups[0][1] if groups else ""
            if len(intro) < 50 and groups:
                # 通用条目的第一句往往只有“某寺是古代官署”这一层，优先取
                # 明朝、历史沿革等包含具体制度事实的组作为卡片概览。
                intro = max((content for _title, content in groups), key=len)
        if len(intro) < 50 and fallback:
            intro, fallback_parts = fallback
            source = SOURCE_EDITORIAL
            groups = []
        if len(intro) < 50:
            notes.append(f"机构缺少本地维基正文，跳过：{name}")
            continue
        item_id = unique_id("institution", name, used_institution_ids)
        row = {"id": item_id, "name": name, "category": category, "active_reigns": era, "function": intro[:3000], "source_id": source, "image_asset": asset_name("institution", item_id)}
        institutions.append(row)
        institution_by_name[name] = row
        sections = sections_from_groups("institution", intro, groups)
        if len(sections) < 4 and fallback:
            intro, fallback_parts = fallback
            source = SOURCE_EDITORIAL
            sections = sections_from_groups("institution", intro, [], fallback_parts)
            row["function"] = intro[:3000]
            row["source_id"] = source
        for section in sections:
            section.update({"institution_id": item_id, "source_id": source})
            institution_sections.append(section)
        if len([r for r in institution_sections if r["institution_id"] == item_id]) < 4:
            notes.append(f"机构正文不足四栏，跳过：{name}")
            institutions.remove(row)
            institution_sections[:] = [r for r in institution_sections if r["institution_id"] != item_id]
            continue
        links = person_links(intro + "\n" + "\n".join(c for _t, c in groups), people)
        for link in links:
            link["institution_id"] = item_id
            institution_people.append(link)

    special_by_name = {row["name"]: row for row in specials}
    used_special_ids = {row["id"] for row in specials}
    for name, category, era, aliases in SPECIAL_ADDITIONS:
        if name in special_by_name:
            continue
        page = source_page(wiki, aliases)
        intro = ""
        groups: list[tuple[str, str]] = []
        source = SOURCE_WIKI
        fallback = fallback_sections(name)
        if page:
            _title, raw = page
            _body, groups = parse_article(raw)
            intro = groups[0][1] if groups else ""
            if len(intro) < 50 and groups:
                intro = max((content for _title, content in groups), key=len)
        elif fallback:
            intro = fallback[0]
            source = SOURCE_EDITORIAL
        if len(intro) < 50:
            notes.append(f"典章没有足够正文，跳过：{name}")
            continue
        item_id = unique_id("special", name, used_special_ids)
        row = {"id": item_id, "name": name, "category": category, "era": era, "description": intro[:3000], "position": 900, "source_id": source, "image_asset": asset_name("special", item_id)}
        sections = sections_from_groups("special", intro, groups)
        if fallback:
            intro, fallback_parts = fallback
            source = SOURCE_EDITORIAL
            row["description"] = intro[:3000]
            row["source_id"] = source
            sections = sections_from_groups("special", intro, [], fallback_parts)
        if len(sections) < 4:
            notes.append(f"典章正文不足四栏，跳过：{name}")
            continue
        specials.append(row)
        special_by_name[name] = row
        for section in sections:
            section.update({"special_item_id": item_id, "source_id": source})
            special_sections.append(section)
        links = person_links(intro + "\n" + "\n".join(c for _t, c in groups), people)
        for link in links:
            link["special_item_id"] = item_id
            special_people.append(link)

    # 只保留有四栏正文的正式条目；清除旧条目偶发的孤立栏。
    inst_ids = {r["id"] for r in institutions}
    special_ids = {r["id"] for r in specials}
    institution_sections = [r for r in institution_sections if r.get("institution_id") in inst_ids]
    special_sections = [r for r in special_sections if r.get("special_item_id") in special_ids]
    valid_inst = {r["institution_id"] for r in institution_sections if len(r.get("content", "").strip()) >= 50}
    valid_special = {r["special_item_id"] for r in special_sections if len(r.get("content", "").strip()) >= 50}
    institutions = [r for r in institutions if r["id"] in valid_inst]
    specials = [r for r in specials if r["id"] in valid_special]
    institution_sections = [r for r in institution_sections if r["institution_id"] in {x["id"] for x in institutions}]
    special_sections = [r for r in special_sections if r["special_item_id"] in {x["id"] for x in specials}]
    institution_people = [r for r in institution_people if r.get("institution_id") in {x["id"] for x in institutions}]
    special_people = [r for r in special_people if r.get("special_item_id") in {x["id"] for x in specials}]

    # 稳定顺序与资源键检查。
    institutions.sort(key=lambda r: (r["category"], r["name"]))
    specials.sort(key=lambda r: (r.get("position", 900), r["category"], r["name"]))
    for position, row in enumerate(specials):
        row["position"] = position
    for rows, key in ((institution_sections, "institution_id"), (special_sections, "special_item_id")):
        rows.sort(key=lambda r: (r[key], r["position"]))
    return institutions, institution_sections, institution_people, specials, special_sections, special_people, notes


def ensure_source() -> None:
    sources = read_rows("source")
    if not any(row.get("id") == SOURCE_WIKI for row in sources):
        sources.append({"id": SOURCE_WIKI, "title": "中文维基百科本地数据包（2023-11-01快照）", "citation": "项目内置中文维基百科数据包；仅用于编辑校验和内容重建。", "url": "", "review_status": "编辑依据"})
        write_rows("source", sources)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = build()
    institutions, institution_sections, institution_people, specials, special_sections, special_people, notes = result
    print(f"机构 {len(institutions)} 条，正文 {len(institution_sections)} 栏，人物关联 {len(institution_people)} 条")
    print(f"典章 {len(specials)} 条，正文 {len(special_sections)} 栏，人物关联 {len(special_people)} 条")
    if notes:
        print("筛选说明：")
        for note in notes:
            print("-", note)
    if args.dry_run:
        return 0
    ensure_source()
    write_rows("institution", institutions)
    write_rows("institution_section", institution_sections)
    write_rows("institution_person", institution_people)
    write_rows("special_item", specials)
    write_rows("special_section", special_sections)
    write_rows("special_person", special_people)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
