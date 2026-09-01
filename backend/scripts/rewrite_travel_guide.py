#!/usr/bin/env python3
"""重写穿越手册：每条约目统一为「明代所用 / 今人做法 / 改良建议」三段。

依据：本地中文维基快照（肥皂·胰子、烧酒·花露、琉璃、筒车、雕版印刷、
火铳、腊肉、酱油、造纸术、天工开物、农政全书）+ 现代来源（CDC/FAO/
NCHFP/NCBI/CMOG/NPS/LOC/DOE/OSHA）。
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]  # backend/

GUIDES = [
    {
        "id": "guide-soap", "category": "卫生", "position": 0,
        "image_asset": "guide_soap",
        "title": "肥皂与洗手",
        "subtitle": "从胰子皂角到稳定清洁",
        "description": "明代以胰子、皂角与草木灰清洁；把洗手做成固定流程，比神奇配方更可靠。",
        "source_id": "guide-handwashing-cdc-v1",
        "sections": [
            ("ming", "胰子与皂角", "guide-soap", 0,
             "明代没有现代肥皂。北方以猪胰脏、板油与碱捣制晒干成\u201c胰子\u201d，南方多用皂角、草木灰水洗衣；沐浴则用澡豆、皂荚。清洁以去油去垢为主，尚无杀菌概念，洗手与否全凭个人习惯。",
             "wikipedia-zh-20231101"),
            ("modern", "流水与皂化", "guide-soap", 1,
             "现代肥皂是油脂与碱的皂化产物，配合流动水搓洗可带走污物与多数微生物；洗手时机集中在做饭前后、如厕后与照护病人前后。它是日常流程，不是药物，也不替代干净水源。",
             "guide-handwashing-cdc-v1"),
            ("improve", "清洁当先", "guide-soap", 2,
             "穿越后应优先推广洗手时机、分区与记录，而非把肥皂说成神效药品；作坊制皂需保证原料来处、每批重量与用途说明一致，账簿记下制作日期与去向，才能查出问题出在哪一批。",
             "guide-handwashing-cdc-v1"),
        ],
    },
    {
        "id": "guide-water", "category": "卫生", "position": 1,
        "image_asset": "guide_water",
        "title": "饮水处理与储存",
        "subtitle": "先取净水，再防二次污染",
        "description": "明代饮井河之水，煮沸沉淀是主要防线；带盖容器与专用取水工具防止再次污染。",
        "source_id": "guide-water-cdc-v1",
        "sections": [
            ("ming", "井河与煮沸", "guide-water", 0,
             "明代城镇多取井水、河水与泉水，讲究\u201c水须煮沸\u201d再饮，是普遍的卫生常识；大户设沉淀缸澄清，或用多层纱布过滤。生水与熟水分开存放，水缸加盖防止落尘。",
             "wikipedia-zh-20231101"),
            ("modern", "沉淀过滤消毒", "guide-water", 1,
             "现代自来水经混凝、沉淀、过滤与消毒四步处理；储水要点是带盖容器、专用取水瓢与定期清洗，防止处理过的水在储存与取用中再次受污染。",
             "guide-water-cdc-v1"),
            ("improve", "每日检查", "guide-water", 2,
             "改良应把\u201c沉淀、过滤、煮沸\u201d串成固定流程；储水缸加盖、取水不入缸、洗手排水与储水处分离，并将容器加盖、水色异味、周边是否积污列为每日检查项。",
             "guide-water-cdc-v1"),
        ],
    },
    {
        "id": "guide-farming", "category": "农事", "position": 2,
        "image_asset": "guide_farming",
        "title": "堆肥、绿肥与轮作",
        "subtitle": "用地力换持续收成",
        "description": "明代以粪肥、绿肥与轮作养地；记录地块与前茬，才能分辨哪种做法真正有效。",
        "source_id": "nongzheng-quanshu-v1",
        "sections": [
            ("ming", "粪肥与换茬", "guide-farming", 0,
             "《农政全书》《沈氏农书》详记粪肥沤制、绿肥种植与轮作换茬；江南精耕细作，以人畜粪、草木灰与豆科绿肥维持地力，靠茬口安排减少连作之害。",
             "nongzheng-quanshu-v1"),
            ("modern", "碳氮与固氮", "guide-farming", 1,
             "现代堆肥控制碳氮比、水分与通气；紫云英等绿肥翻压固氮，轮作调节养分与病虫害；测土后按需施肥，避免盲目堆量。",
             "guide-agriculture-fao-v1"),
            ("improve", "记录先行", "guide-farming", 2,
             "改良要点：堆肥远离水源与居住区，不混入病死动物；每块示范田记录前茬、播种、施用与收成，一次只改少数条件并留对照地，积累可复查的经验而非\u201c秘法\u201d。",
             "guide-agriculture-fao-v1"),
        ],
    },
    {
        "id": "guide-food", "category": "生计", "position": 3,
        "image_asset": "guide_food",
        "title": "干燥、腌渍与发酵保藏",
        "subtitle": "把收获保存到淡季",
        "description": "明代用晒干、盐腌、酱制与窖藏延长供应；按食材选法、记批次，才能查出问题。",
        "source_id": "guide-food-nchfp-v1",
        "sections": [
            ("ming", "腊腌酱窖", "guide-food", 0,
             "明代保藏法成熟：腊肉腌晒、咸鱼、酱与酱油发酵、干菜晒制、番薯窖藏（《农政全书》）；冬季储冰供暑月使用，官府民间皆有冰窖。",
             "nongzheng-quanshu-v1"),
            ("modern", "低温与标准", "guide-food", 1,
             "现代以冷藏冷冻、罐藏与标准化干燥为主，靠温度、盐度或酸度控制微生物；工业化生产以杀菌与密封代替\u201c凭经验判断\u201d。",
             "guide-food-nchfp-v1"),
            ("improve", "批次可查", "guide-food", 2,
             "改良应引入容器、日期与批次记录；生料区与成品区分开；容器胀裂、霉斑、异味即停止流通，尝味不是检验安全的方法。",
             "guide-food-nchfp-v1"),
        ],
    },
    {
        "id": "guide-distillation", "category": "工坊", "position": 4,
        "image_asset": "guide_distillation",
        "title": "蒸馏的用途与安全",
        "subtitle": "分离工艺先谈风险",
        "description": "明代烧酒与花露皆出蒸馏；高温蒸气易燃，先明确用途、值守与安全边界。",
        "source_id": "bencao-gangmu-v1",
        "sections": [
            ("ming", "烧酒与花露", "guide-distillation", 0,
             "蒸馏酒元代传入、明代普及，江西李渡烧酒作坊遗址为现存最早实证；《本草纲目》记烧酒；蔷薇露、花露自唐入华，以蒸馏提取香液用于薰衣与药用。",
             "wikipedia-zh-20231101"),
            ("modern", "精馏与规范", "guide-distillation", 1,
             "现代蒸馏以精馏塔提纯，讲究热源、冷却与连续监控；甲醇等杂质有明确毒性分级，饮用酒生产受法规与检测约束。",
             "guide-distillation-safety-v1"),
            ("improve", "安全先行", "guide-distillation", 2,
             "穿越后应先做花露、药露等低风险蒸馏；设备、原料、成品分别登记，热源旁不堆可燃物，异味泄漏即停用；不提供饮用酒精的家庭试验方法与参数。",
             "guide-distillation-safety-v1"),
        ],
    },
    {
        "id": "guide-glass", "category": "工坊", "position": 5,
        "image_asset": "guide_glass",
        "title": "玻璃工艺与透明器具",
        "subtitle": "材料与炉况决定成败",
        "description": "明代玻璃多靠进口，本土琉璃为低温釉陶；透明玻璃取决于原料、炉温与缓冷。",
        "source_id": "guide-glass-cmog-v1",
        "sections": [
            ("ming", "进口玻璃与琉璃", "guide-glass", 0,
             "明代透明玻璃器多来自西洋贸易，价值高昂；本土琉璃是低温玻璃质釉面陶或建筑构件，料器以色料仿玉，透明玻璃难以自制。",
             "wikipedia-zh-20231101"),
            ("modern", "钠钙与退火", "guide-glass", 1,
             "现代玻璃以二氧化硅配钠、钙助熔，熔融后必须缓慢退火消除内应力，否则成品易自裂；原料纯度与炉况决定透明度与气泡。",
             "guide-glass-cmog-v1"),
            ("improve", "先小后稳", "guide-glass", 2,
             "改良应优先做瓶罐、窗片、灯罩等用途明确的器具；把原料、热作、成形、缓冷与检查分段管理；没有稳定炉况与缓冷条件，不做高温玻璃试验。",
             "guide-glass-cmog-v1"),
        ],
    },
    {
        "id": "guide-mortar", "category": "建造", "position": 6,
        "image_asset": "guide_mortar",
        "title": "石灰砂浆与砌体维护",
        "subtitle": "先排水，再补缝",
        "description": "明代用石灰、糯米灰浆与三合土砌筑；修补要问材料相容与排水，而非一味求硬。",
        "source_id": "guide-masonry-nps-v1",
        "sections": [
            ("ming", "石灰与糯米浆", "guide-mortar", 0,
             "明代石灰烧制成熟，糯米汁掺石灰成\u201c糯米灰浆\u201d，用于城墙、陵墓等大型砌筑；三合土以石灰、土、砂配比夯筑墙体与地面，讲究灰土比例与分层夯实。",
             "wikipedia-zh-20231101"),
            ("modern", "水泥与相容性", "guide-mortar", 1,
             "现代波特兰水泥强度高但透气差，用于旧砌体常造成盐析与开裂；古建修复强调材料相容、可逆与排水优先，石灰基材料仍是旧墙修补的首选。",
             "guide-masonry-nps-v1"),
            ("improve", "排水先行", "guide-mortar", 2,
             "修补前先查屋面、排水沟与地面坡度，水的问题不解决，补缝难以持久；大面积修补先做小样，承重墙与窑炉结构由熟悉当地材料的人复核。",
             "guide-masonry-nps-v1"),
        ],
    },
    {
        "id": "guide-printing", "category": "传播", "position": 7,
        "image_asset": "guide_printing",
        "title": "纸张、刻版与账簿",
        "subtitle": "让信息可复制、可复查",
        "description": "明代雕版与竹纸成熟；试印、校对与账簿记录，比华丽装帧更有实际价值。",
        "source_id": "tiangong-kaiwu-v1",
        "sections": [
            ("ming", "雕版与竹纸", "guide-printing", 0,
             "明代雕版印刷鼎盛，坊刻、套印并行，竹纸价廉普及；木活字、铜活字已有应用，《天工开物》记造纸工序；书坊刻本流传广、成本低。",
             "tiangong-kaiwu-v1"),
            ("modern", "定稿与版次", "guide-printing", 1,
             "现代出版流程为定稿、制版、试印、校对、正式印刷与存档；每次改动标明版次与日期，样张留存，账簿栏目固定。",
             "guide-printing-loc-v1"),
            ("improve", "先印实用", "guide-printing", 2,
             "价目表、契约格式、农时表、作坊规程与账簿表格，比大部头著作更适合小型印坊；涉及医疗、税赋、契约与军务的内容反复校对，不把传闻印成事实。",
             "guide-printing-loc-v1"),
        ],
    },
    {
        "id": "guide-waterpower", "category": "机械", "position": 8,
        "image_asset": "guide_waterpower",
        "title": "水车与传动装置",
        "subtitle": "把水流变成可维护的动力",
        "description": "明代筒车提水、水磨碾米；先看水量季节与维修条件，再谈传动与出力。",
        "source_id": "guide-waterpower-doe-v1",
        "sections": [
            ("ming", "筒车与翻车", "guide-waterpower", 0,
             "筒车（水转提水）唐代已有、明代在南方普及；龙骨水车（翻车）以人力畜力驱动用于灌溉；水碾、水磨借水力加工谷物，是明代常见机械。",
             "wikipedia-zh-20231101"),
            ("modern", "水泵与规范", "guide-waterpower", 1,
             "现代以离心泵提水、水轮机发电，讲究流量、扬程与维护周期；设备有明确的停机与检修程序，检修前先切断动力并挂牌隔离。",
             "guide-waterpower-doe-v1"),
            ("improve", "单用先稳", "guide-waterpower", 2,
             "改良先让单一用途（碾米或提水）稳定，再考虑多工序联动；动工前看水量枯洪变化与零件可否就地修复；图样、尺寸与维修日期随设备记录，检修前先停机隔离。",
             "guide-waterpower-doe-v1"),
        ],
    },
    {
        "id": "guide-metallurgy-safety", "category": "安全", "position": 9,
        "image_asset": "guide_metallurgy_safety",
        "title": "铁作工坊与危险器材管理",
        "subtitle": "先建安全工坊，再谈器物产出",
        "description": "明代炒钢灌钢技术成熟；危险器材不得私自处理，工坊分区管理，先安全后产出。",
        "source_id": "guide-metalwork-osha-v1",
        "sections": [
            ("ming", "炒钢与灌钢", "guide-metallurgy-safety", 0,
             "《天工开物》记明代铁艺：炒钢、灌钢、苏钢并用，铁作供应农具、锅釜与兵器；火铳等火器已入军用，鄱阳湖之战即用火器。",
             "tiangong-kaiwu-v1"),
            ("modern", "分区与防护", "guide-metallurgy-safety", 1,
             "现代金属加工把热作区、材料区、成品区与维修区分开，配通风、护目与隔离；高温、粉尘、重物搬运皆有规程，防护设施不因方便拆除。",
             "guide-metalwork-osha-v1"),
            ("improve", "只谈隔离", "guide-metallurgy-safety", 2,
             "火器、弹药、爆炸物与来源不明压力容器不属于个人工坊，发现即远离并联系具备处置资格的人员；本条绝不提供火器、弹药、爆炸物的配方、尺寸、装配与维修方法。",
             "guide-metalwork-osha-v1"),
        ],
    },
]

NEW_SOURCES = [
    {
        "id": "tiangong-kaiwu-v1",
        "title": "《天工开物》（1637，宋应星）",
        "url": "https://zh.wikipedia.org/wiki/天工开物",
        "citation": "明代工农业技术总录：造纸、冶炼、烧制等",
        "review_status": "资料已登记",
    },
    {
        "id": "nongzheng-quanshu-v1",
        "title": "《农政全书》（1639，徐光启）",
        "url": "https://zh.wikipedia.org/wiki/农政全书",
        "citation": "明代农学总汇：粪肥、绿肥、窖藏等",
        "review_status": "资料已登记",
    },
    {
        "id": "bencao-gangmu-v1",
        "title": "《本草纲目》（1596，李时珍）",
        "url": "https://zh.wikipedia.org/wiki/本草纲目",
        "citation": "明代药物学：烧酒、花露等条目",
        "review_status": "资料已登记",
    },
]


def main() -> None:
    guide_rows, section_rows = [], []
    for guide in GUIDES:
        guide_rows.append({
            "id": guide["id"], "category": guide["category"], "title": guide["title"],
            "subtitle": guide["subtitle"], "description": guide["description"],
            "image_asset": guide["image_asset"], "position": guide["position"],
            "source_id": guide["source_id"],
        })
        for key, sec_title, gid, pos, content, source_id in guide["sections"]:
            section_rows.append({
                "travel_guide_id": gid, "section_key": key, "title": sec_title,
                "content": content, "position": pos, "source_id": source_id,
            })

    def dump(path, rows):
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    dump(str(BASE / "data/content/travel_guide.jsonl"), guide_rows)
    dump(str(BASE / "data/content/travel_guide_section.jsonl"), section_rows)

    sources = [json.loads(line) for line in open(BASE / "data/content/source.jsonl", encoding="utf-8") if line.strip()]
    fresh_sources = {row["id"]: row for row in sources}
    for row in NEW_SOURCES:
        fresh_sources[row["id"]] = row
    dump(str(BASE / "data/content/source.jsonl"), list(fresh_sources.values()))

    print(f"guides: {len(guide_rows)}, sections: {len(section_rows)}, sources: {len(sources)}")


if __name__ == "__main__":
    main()
