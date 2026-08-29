#!/usr/bin/env python3
"""盘点整个数据集里所有明朝相关条目：人、事、物、制度、习俗。

数据源：
- /tmp/wikihf/*.parquet（维基百科 20231101.zh 全量 1.4M 条，含全文）
- sources/mingshi/《明史》332 卷（传主名单骨架）

输出：/tmp/ming_inventory.json（分类清单，供收录脚本使用）
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pyarrow.parquet as pq
from opencc import OpenCC

s2t = OpenCC("s2t")
BACKEND = Path(__file__).resolve().parents[1]
CORPUS = BACKEND.parent / 'sources' / 'mingshi'
PACKS = [Path(__file__).resolve().parents[1] / 'sources' / 'wikipedia_zh' / f"train-0000{i}.parquet" for i in range(6)]

BIO_HEAD = re.compile(r"^([\u4e00-\u9fa5·]{2,4})，")
DATE_CHARS = set("一二三四五六七八九十初春夏秋冬朔晦乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥")

EVENT_TERMS = [
    "靖难之役", "土木之变", "土木堡之变", "夺门之变", "曹石之变", "大礼议", "壬寅宫变",
    "庚戌之变", "隆庆开关", "俺答封贡", "万历三大征", "宁夏之役", "朝鲜之役", "万历朝鲜之役",
    "播州之役", "萨尔浒之战", "宁远之战", "宁锦之战", "己巳之变", "松锦之战", "郑和下西洋",
    "郭桓案", "空印案", "胡惟庸案", "胡惟庸之乱", "蓝玉案", "李福达案", "妖书案", "梃击案",
    "红丸案", "移宫案", "东林党争", "国本之争", "矿税之弊", "白莲教起义", "唐赛儿起义",
    "邓茂七起义", "叶宗留起义", "刘六刘七起义", "明末农民战争", "李自成起义", "张献忠起义",
    "嘉靖倭乱", "倭寇", "戚继光抗倭", "援朝战争", "明成祖北征", "永乐迁都", "靖难",
    "土木堡", "南明", "弘光", "隆武", "永历", "鲁监国", "明郑", "迁海令", "剃发易服",
    "三饷", "一条鞭法", "考成法", "隆庆新政", "弘治中兴", "仁宣之治", "永乐盛世",
    "万历中兴", "崇祯", "甲申之变", "清军入关", "扬州十日", "嘉定三屠",
]
OBJECT_TERMS = [
    "永乐大典", "明长城", "明十三陵", "明孝陵", "南京故宫", "紫禁城", "故宫",
    "宣德炉", "青花瓷", "大明宝钞", "宝钞", "郑和宝船", "宝船", "佛郎机", "红夷大炮",
    "火铳", "神机营", "丹书铁券", "尚方宝剑", "王命旗牌", "乌纱帽", "补子",
    "明式家具", "明代瓷器", "吴门四家", "江南四大才子", "吴中四才子", "明代家具",
]
SYSTEM_TERMS = [
    "明朝内阁", "内阁", "司礼监", "锦衣卫", "东厂", "西厂", "内行厂", "六科给事中",
    "都察院", "通政使司", "大理寺", "翰林院", "国子监", "钦天监", "太医院",
    "五军都督府", "卫所制", "卫所", "都指挥使司", "承宣布政使司", "提刑按察使司",
    "总督", "巡抚", "科举", "乡试", "会试", "殿试", "八股文", "庶吉士", "廷杖",
    "诏狱", "大明律", "大明会典", "皇明祖训", "大诰", "黄册", "鱼鳞图册", "里甲制",
    "匠户制度", "海禁", "宗藩条例", "殉葬", "内书堂", "厂卫", "明朝政治制度",
    "明朝官制", "明朝科举", "明朝经济", "明朝军事", "明朝外交", "明朝文化",
    "明朝科技", "明朝历史", "明朝君主", "明朝皇帝", "南明",
]
CUSTOM_TERMS = [
    "明朝服饰", "明代服饰", "明朝饮食", "明代婚礼", "明朝科举制度", "冠礼",
    "明朝宗教", "明代小说", "明代戏曲", "昆曲", "明朝建筑", "明代丧葬",
]


def main() -> int:
    # 1) 明史传主骨架
    heads: list[str] = []
    for f in sorted(CORPUS.glob("卷*.txt")):
        juan = int(f.stem[1:])
        # 卷300-332 为土司传与外国传，所记为政权而非人物，一并排除
        if juan < 113 or juan >= 300:
            continue
        text = f.read_text(encoding="utf-8")
        for para in text.split("\n"):
            m = BIO_HEAD.match(para)
            if not m:
                continue
            name = m.group(1)
            if set(name) & DATE_CHARS:
                continue
            heads.append(name)
    head_set_s = set(heads)
    head_set_t = {s2t.convert(n) for n in head_set_s}

    # 2) 扫全部维基标题
    people_hits: dict[str, dict] = {}
    event_hits: dict[str, dict] = {}
    object_hits: dict[str, dict] = {}
    system_hits: dict[str, list] = {}
    custom_hits: dict[str, list] = {}
    ming_prefix: list[str] = []
    total_rows = 0

    def term_lookup(title: str, terms: list[str]) -> str | None:
        if title in terms:
            return title
        for t in terms:
            if title.startswith(t + " (") or title.startswith(t + "（"):
                return t
        return None

    for pack in PACKS:
        table = pq.read_table(str(pack), columns=["title", "text"])
        for title, text in zip(table.column("title").to_pylist(), table.column("text").to_pylist()):
            total_rows += 1
            if title in head_set_s or title in head_set_t:
                key = s2t.convert(title)
                people_hits.setdefault(key, {"wiki_title": title, "text_len": len(text), "juans": []})
            for terms, bucket in (
                (EVENT_TERMS, event_hits),
                (OBJECT_TERMS, object_hits),
            ):
                term = term_lookup(title, terms)
                if term:
                    bucket.setdefault(term, {"wiki_title": title, "text_len": len(text)})
            for term in SYSTEM_TERMS:
                if title == term or title.startswith(term + " ("):
                    system_hits.setdefault(term, []).append(title)
            for term in CUSTOM_TERMS:
                if title == term or title.startswith(term + " ("):
                    custom_hits.setdefault(term, []).append(title)
            if title.startswith(("明朝", "明代", "南明")) and len(title) <= 14:
                ming_prefix.append(title)

    print(f"维基总条目 {total_rows}")
    print(f"人物（明史传主 ∩ 维基词条）: {len(people_hits)}")
    print(f"事件（术语命中）: {len(event_hits)} -> {sorted(event_hits)[:12]}")
    print(f"器物（术语命中）: {len(object_hits)} -> {sorted(object_hits)[:12]}")
    print(f"制度专题: {len(system_hits)} -> {sorted(system_hits)[:14]}")
    print(f"习俗文化: {len(custom_hits)} -> {sorted(custom_hits)[:10]}")
    print(f"'明朝/明代/南明'前缀条目: {len(ming_prefix)} -> {sorted(set(ming_prefix))[:20]}")

    inventory = {
        "people": {k: v for k, v in sorted(people_hits.items())},
        "events": {k: v for k, v in sorted(event_hits.items())},
        "objects": {k: v for k, v in sorted(object_hits.items())},
        "systems": {k: v for k, v in sorted(system_hits.items())},
        "customs": {k: v for k, v in sorted(custom_hits.items())},
        "ming_prefix_titles": sorted(set(ming_prefix)),
    }
    Path("/tmp/ming_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=1), encoding="utf-8")
    total = len(people_hits) + len(event_hits) + len(object_hits) + len(set(system_hits)) + len(set(custom_hits))
    print(f"合计可收录（不含前缀专题）: {total} 条 → /tmp/ming_inventory.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
