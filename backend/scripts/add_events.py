#!/usr/bin/env python3
"""补建缺失的历史事件：把仅以亲属/名臣身份存在、尚无事件条目的人物纳入事件参与者池。

依据维基百科人物条目的可考史实（内容登记于 person_wiki.jsonl）：
- 台州抗倭：嘉靖三十七年（1558）谭纶守台州三战三捷，戚继光协防浙东；
- 兴化之战：嘉靖四十二年（1563）谭纶任总指挥，戚继光、俞大猷、刘显分头进攻，收复兴化；
- 仙游之战：嘉靖四十三年（1564）谭纶率戚继光部增援仙游，斩敌千余。

第一轮：嘉靖抗倭（戚继光/俞大猷/谭纶）；第二轮：刘瑾专权、张居正改革、严嵩构陷王世贞。
纯新增事件，不改动既有事件。
"""
from __future__ import annotations

import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"


def read_jsonl(name: str) -> list[dict]:
    return [json.loads(l) for l in (CONTENT / name).open(encoding="utf-8")]


def write_jsonl(name: str, rows: list[dict]) -> None:
    rows.sort(key=lambda r: (r.get("year") or 0, r.get("title") or ""))
    with (CONTENT / name).open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


EVENTS = [
    {
        "id": "wiki-event-taizhoukangwo-1558",
        "title": "台州抗倭",
        "year": 1558,
        "month": "全年",
        "event_type": "战争与边防",
        "place": "浙江台州府",
        "reign_id": "jiajing",
        "participants": "谭纶、戚继光、胡宗宪",
        "summary": "嘉靖三十六年至三十七年（1557—1558），倭寇屡犯浙江台州。台州知府谭纶招募乡勇、练兵御倭，嘉靖三十七年亲率死士与倭寇大战，三战三捷，军威大振；戚继光此时以参将协防浙东，受浙江总督胡宗宪节制，与谭纶同练乡兵抗倭。",
        "detail": (
            "背景\n"
            "嘉靖中叶，东南沿海倭患炽烈。倭寇勾结内地海商，屡犯浙江、福建沿海州县，朝廷选将练兵，加强海防。台州府地处浙东，濒海多港，为倭寇进犯要冲。\n"
            "经过\n"
            "嘉靖二十九年（1550年），谭纶受命任台州知府，招募乡勇千人，练兵御倭，升浙江按察司海道副使。嘉靖三十六年（1557年），谭纶率兵在台州大挫倭寇。次年，倭寇率数万人再犯台州，谭纶亲率死士出战，三战三捷，军威大振。与此同时，戚继光于嘉靖三十五年（1556年）升任参将，负责钱塘江以东防务，支援宁波、绍兴、台州三府，与谭纶一同训练乡兵。台州一役后，戚继光所练戚家军声名渐起。\n"
            "结果\n"
            "台州倭患暂告平定，谭纶以功加右参政；戚继光此后继续练兵，于嘉靖四十年（1561年）在台州九战九捷，彻底肃清浙东倭患。"
        ),
        "consequence": "谭纶与戚继光由此结为抗倭将帅中的搭档，谭纶此后屡次举荐戚继光。",
        "source_id": "wikipedia-zh-20231101",
        "end_year": 1558,
    },
    {
        "id": "wiki-event-xinghuazhizhan-1563",
        "title": "兴化之战",
        "year": 1563,
        "month": "春四月",
        "event_type": "战争与边防",
        "place": "福建兴化府",
        "reign_id": "jiajing",
        "participants": "谭纶、戚继光、俞大猷、刘显、汪道昆",
        "summary": "嘉靖四十二年（1563年），倭寇陷福建兴化。巡抚福建的谭纶任总指挥，命戚继光、俞大猷、刘显分头进攻，一举灭敌二千余，收复兴化城。",
        "detail": (
            "背景\n"
            "嘉靖四十一年（1562年），福建沿海倭患复炽，倭寇在邵武、兴化一带大肆劫掠，兴化府城一度陷落，东南震动。\n"
            "经过\n"
            "嘉靖四十二年（1563年）春，起复丁忧中的谭纶，以原官兼按察司佥事，统浙兵一千二百人入闽，与都督刘显、总兵俞大猷会剿。三月，谭纶擢右佥都御史，巡抚福建，举荐戚继光、俞大猷等参战。四月，谭纶任总指挥，命戚、俞等分头进攻，明军一举歼敌二千余，收复兴化城。\n"
            "结果\n"
            "兴化光复，福建倭势受挫。谭纶自此与戚继光、俞大猷在闽浙军务中密切配合，至嘉靖末年基本肃清东南倭患。"
        ),
        "consequence": "戚继光升任都督同知，后为福建总兵；俞大猷以福建总兵会剿，二人并称抗倭名将。",
        "source_id": "wikipedia-zh-20231101",
        "end_year": 1563,
    },
    {
        "id": "wiki-event-xianyouzhizhan-1564",
        "title": "仙游之战",
        "year": 1564,
        "month": "春",
        "event_type": "战争与边防",
        "place": "福建仙游县",
        "reign_id": "jiajing",
        "participants": "谭纶、戚继光、汪道昆",
        "summary": "嘉靖四十三年（1564年），倭寇再攻福建仙游。谭纶亲率戚继光部增援，攻下仙游，斩敌千余，迫使倭寇余部入海逃遁。",
        "detail": (
            "背景\n"
            "兴化之战后，福建倭寇余部并未尽灭。嘉靖四十三年（1564年），倭寇卷土重来，围攻仙游县城，形势危急。\n"
            "经过\n"
            "时任福建巡抚的谭纶闻警，亲率戚继光部驰援仙游。明军内外夹击，攻破倭营，斩敌千余，仙游围解。\n"
            "结果\n"
            "倭寇余部被迫入海逃遁，福建倭患自此基本肃清。谭纶以功督两广军务，戚继光留镇闽浙。"
        ),
        "consequence": "东南倭患平定，戚继光、俞大猷、谭纶的抗倭功业告成。",
        "source_id": "wikipedia-zh-20231101",
        "end_year": 1564,
    },
]

PARTICIPANTS = {
    "wiki-event-taizhoukangwo-1558": [
        ("tanlun", "决策者"),
        ("qijiguang", "主将"),
        ("huzongxian", "决策者"),
    ],
    "wiki-event-xinghuazhizhan-1563": [
        ("tanlun", "总指挥"),
        ("qijiguang", "主将"),
        ("yudayou", "主将"),
        ("liuxian", "主将"),
        ("wangdaokun", "监军"),
    ],
    "wiki-event-xianyouzhizhan-1564": [
        ("tanlun", "决策者"),
        ("qijiguang", "主将"),
        ("wangdaokun", "监军"),
    ],
}


SECTIONS = {
    "wiki-event-taizhoukangwo-1558": [
        ("background", "背景", "嘉靖中叶，东南沿海倭患炽烈。倭寇勾结内地海商，屡犯浙江、福建沿海州县，朝廷选将练兵，加强海防。台州府地处浙东，濒海多港，为倭寇进犯要冲。"),
        ("course", "经过", "嘉靖二十九年（1550年），谭纶受命任台州知府，招募乡勇千人，练兵御倭，升浙江按察司海道副使。嘉靖三十六年（1557年），谭纶率兵在台州大挫倭寇。次年，倭寇率数万人再犯台州，谭纶亲率死士出战，三战三捷，军威大振。与此同时，戚继光于嘉靖三十五年（1556年）升任参将，负责钱塘江以东防务，支援宁波、绍兴、台州三府，与谭纶一同训练乡兵。台州一役后，戚继光所练戚家军声名渐起。"),
        ("result", "结果", "台州倭患暂告平定，谭纶以功加右参政；戚继光此后继续练兵，于嘉靖四十年（1561年）在台州九战九捷，彻底肃清浙东倭患。"),
        ("people", "相关人物", "谭纶、戚继光、胡宗宪"),
    ],
    "wiki-event-xinghuazhizhan-1563": [
        ("background", "背景", "嘉靖四十一年（1562年），福建沿海倭患复炽，倭寇在邵武、兴化一带大肆劫掠，兴化府城一度陷落，东南震动。"),
        ("course", "经过", "嘉靖四十二年（1563年）春，起复丁忧中的谭纶，以原官兼按察司佥事，统浙兵一千二百人入闽，与都督刘显、总兵俞大猷会剿。三月，谭纶擢右佥都御史，巡抚福建，举荐戚继光、俞大猷等参战。四月，谭纶任总指挥，命戚、俞等分头进攻，明军一举歼敌二千余，收复兴化城。"),
        ("result", "结果", "兴化光复，福建倭势受挫。谭纶自此与戚继光、俞大猷在闽浙军务中密切配合，至嘉靖末年基本肃清东南倭患。"),
        ("people", "相关人物", "谭纶、戚继光、俞大猷、刘显、汪道昆"),
    ],
    "wiki-event-xianyouzhizhan-1564": [
        ("background", "背景", "兴化之战后，福建倭寇余部并未尽灭。嘉靖四十三年（1564年），倭寇卷土重来，围攻仙游县城，形势危急。"),
        ("course", "经过", "时任福建巡抚的谭纶闻警，亲率戚继光部驰援仙游。明军内外夹击，攻破倭营，斩敌千余，仙游围解。"),
        ("result", "结果", "倭寇余部被迫入海逃遁，福建倭患自此基本肃清。谭纶以功督两广军务，戚继光留镇闽浙。"),
        ("people", "相关人物", "谭纶、戚继光、汪道昆"),
    ],
}


EVENTS += [
    {
        "id": "wiki-event-liujinzhuanquan-1510",
        "title": "刘瑾专权",
        "year": 1510,
        "month": "正德元年至五年",
        "event_type": "宫廷政争",
        "place": "京师",
        "reign_id": "zhengde",
        "participants": "刘瑾、李东阳、刘健、谢迁、朱厚照、杨一清、仇钺",
        "summary": "正德初年，司礼监太监刘瑾得武宗宠信，把持朝政，排挤内阁。刘健、谢迁、李东阳等顾命大臣欲诛刘瑾不成，刘健、谢迁被迫致仕。正德五年（1510年）安化王朱寘鐇以讨刘瑾为名起兵，杨一清借机与张永定计，刘瑾伏诛。",
        "detail": (
            "背景\n"
            "明武宗朱厚照即位后，宠信以刘瑾为首的宦官，刘瑾升任司礼监掌印太监，勾结党羽把持朝政，与内阁顾命大臣刘健、谢迁、李东阳势成水火。\n"
            "经过\n"
            "刘健、谢迁等密谋去除宦官，事泄反被刘瑾构陷，先后被迫致仕。刘瑾诏列五十三人为奸党，榜示朝堂，以刘健为首，又削其籍、追夺诰命。李东阳虽在朝中周旋，亦多次求去而未获准。正德五年（1510年），安化王朱寘鐇以讨刘瑾为名起兵，都御史杨一清与太监张永定计，回京后揭发刘瑾十七大罪，刘瑾被磔于市。\n"
            "结果\n"
            "刘瑾伏诛，其党羽被清除，谢迁官复原职，李东阳继续在内阁。朝政一度归于正轨。"
        ),
        "consequence": "刘瑾伏诛后，正德朝政短暂清明；谢迁、刘健等旧臣得平反。",
        "source_id": "wikipedia-zh-20231101",
        "end_year": 1510,
    },
    {
        "id": "wiki-event-zhangjuzhenggaige-1582",
        "title": "张居正改革",
        "year": 1582,
        "month": "万历元年至十年",
        "event_type": "建制与法令",
        "place": "京师",
        "reign_id": "wanli",
        "participants": "张居正、朱翊钧、冯保、申时行",
        "summary": "万历初年，内阁首辅张居正与司礼监掌印太监冯保内外相结，辅佐年幼的神宗推行改革：清丈土地、推行一条鞭法、整顿吏治，史称万历新政。张居正死后遭清算，申时行继任首辅。",
        "detail": (
            "背景\n"
            "隆庆六年（1572年）穆宗驾崩，十岁的朱翊钧即位，是为神宗。司礼监冯保与内阁首辅张居正同受顾命，内外呼应，掌握朝政。\n"
            "经过\n"
            "张居正任首辅十年，推行考成法整顿吏治，清丈全国田亩，在全国推广一条鞭法，减免冗费，充实国库；又任用戚继光等整顿边防，起用潘季驯治理黄河。冯保在内廷配合，皇帝对张居正言听计从。\n"
            "结果\n"
            "万历十年（1582年）张居正病逝，随即遭言官清算，家产被抄，改革多被废止。申时行继任内阁首辅，以调和持重维系朝局。"
        ),
        "consequence": "万历初年府库充盈、边防稳固的十年新政，因张居正身后被清算而中衰。",
        "source_id": "wikipedia-zh-20231101",
        "end_year": 1582,
    },
    {
        "id": "wiki-event-yansonggouxianwangshi-1560",
        "title": "严嵩构陷王世贞",
        "year": 1560,
        "month": "嘉靖三十九年",
        "event_type": "宫廷政争",
        "place": "京师",
        "reign_id": "jiajing",
        "participants": "王世贞、王忬、严嵩、朱厚熜",
        "summary": "嘉靖三十九年（1560年），蓟辽总督王忬因得罪权臣严嵩，被罗织罪名下狱处决；其子王世贞弃官持丧，后成文坛领袖。此案为嘉靖朝严嵩专权时期的一大冤狱。",
        "detail": (
            "背景\n"
            "严嵩把持内阁，排除异己。王忬官至蓟辽总督，守边有声，因不附严嵩父子而遭忌恨。\n"
            "经过\n"
            "嘉靖三十八年（1559年），鞑靼兵犯蓟辽，严嵩党羽借机弹劾王忬失职，王忬被逮下狱。其子王世贞与弟王世懋奔走营救，严嵩置若罔闻。嘉靖三十九年（1560年），王忬被处决。\n"
            "结果\n"
            "王忬冤死后，王世贞弃官持丧，与李攀龙等并称后七子，领袖文坛，其著作《弇州山人四部稿》影响深远。严嵩倒台后，王忬得平反，追复原官。"
        ),
        "consequence": "严嵩败落后王忬平反，王世贞以文学名世，是嘉靖文坛与政治交织的典型事件。",
        "source_id": "wikipedia-zh-20231101",
        "end_year": 1560,
    },
]

PARTICIPANTS.update({
    "wiki-event-liujinzhuanquan-1510": [
        ("liujin", "主谋"),
        ("liudongyang", "阁臣"),
        ("liujian", "阁臣"),
        ("xieqian", "阁臣"),
        ("zhuhouzhao", "皇帝"),
        ("yangyiqing", "都御史"),
        ("chouyue", "武将"),
    ],
    "wiki-event-zhangjuzhenggaige-1582": [
        ("zhangjuzheng", "首辅"),
        ("zhuyijun", "皇帝"),
        ("fengbao", "司礼监掌印"),
        ("shenshixing", "继任首辅"),
    ],
    "wiki-event-yansonggouxianwangshi-1560": [
        ("wangyu", "蓟辽总督"),
        ("wangshizhen", "受害者之子"),
        ("yansong", "权臣"),
        ("zhuhoucong", "皇帝"),
    ],
})

SECTIONS.update({
    "wiki-event-liujinzhuanquan-1510": [
        ("background", "背景", "明武宗朱厚照即位后，宠信以刘瑾为首的宦官，刘瑾升任司礼监掌印太监，勾结党羽把持朝政，与内阁顾命大臣刘健、谢迁、李东阳势成水火。"),
        ("course", "经过", "刘健、谢迁等密谋去除宦官，事泄反被刘瑾构陷，先后被迫致仕。刘瑾诏列五十三人为奸党，榜示朝堂，以刘健为首，又削其籍、追夺诰命。李东阳虽在朝中周旋，亦多次求去而未获准。正德五年（1510年），安化王朱寘鐇以讨刘瑾为名起兵，都御史杨一清与太监张永定计，回京后揭发刘瑾十七大罪，刘瑾被磔于市。"),
        ("result", "结果", "刘瑾伏诛，其党羽被清除，谢迁官复原职，李东阳继续在内阁。朝政一度归于正轨。"),
        ("people", "相关人物", "刘瑾、李东阳、刘健、谢迁、朱厚照、杨一清、仇钺"),
    ],
    "wiki-event-zhangjuzhenggaige-1582": [
        ("background", "背景", "隆庆六年（1572年）穆宗驾崩，十岁的朱翊钧即位，是为神宗。司礼监冯保与内阁首辅张居正同受顾命，内外呼应，掌握朝政。"),
        ("course", "经过", "张居正任首辅十年，推行考成法整顿吏治，清丈全国田亩，在全国推广一条鞭法，减免冗费，充实国库；又任用戚继光等整顿边防，起用潘季驯治理黄河。冯保在内廷配合，皇帝对张居正言听计从。"),
        ("result", "结果", "万历十年（1582年）张居正病逝，随即遭言官清算，家产被抄，改革多被废止。申时行继任内阁首辅，以调和持重维系朝局。"),
        ("people", "相关人物", "张居正、朱翊钧、冯保、申时行"),
    ],
    "wiki-event-yansonggouxianwangshi-1560": [
        ("background", "背景", "严嵩把持内阁，排除异己。王忬官至蓟辽总督，守边有声，因不附严嵩父子而遭忌恨。"),
        ("course", "经过", "嘉靖三十八年（1559年），鞑靼兵犯蓟辽，严嵩党羽借机弹劾王忬失职，王忬被逮下狱。其子王世贞与弟王世懋奔走营救，严嵩置若罔闻。嘉靖三十九年（1560年），王忬被处决。"),
        ("result", "结果", "王忬冤死后，王世贞弃官持丧，与李攀龙等并称后七子，领袖文坛，其著作《弇州山人四部稿》影响深远。严嵩倒台后，王忬得平反，追复原官。"),
        ("people", "相关人物", "王世贞、王忬、严嵩、朱厚熜"),
    ],
})

def main() -> int:
    events = read_jsonl("event.jsonl")
    existing_ids = {e["id"] for e in events}
    sections = read_jsonl("event_section.jsonl")
    participants = read_jsonl("event_participant.jsonl")
    references = read_jsonl("content_reference.jsonl")

    added_events = []
    for ev in EVENTS:
        if ev["id"] in existing_ids:
            print(f"skip existing: {ev['id']}")
            continue
        events.append(ev)
        added_events.append(ev)
        for position, (key, title, content) in enumerate(SECTIONS[ev["id"]]):
            sections.append(
                {
                    "event_id": ev["id"],
                    "position": position,
                    "section_key": key,
                    "title": title,
                    "content": content,
                }
            )
        for person_id, role in PARTICIPANTS[ev["id"]]:
            participants.append(
                {"event_id": ev["id"], "person_id": person_id, "role": role}
            )

    write_jsonl("event.jsonl", events)
    write_jsonl("event_section.jsonl", sections)
    write_jsonl("event_participant.jsonl", participants)
    print(f"新增事件 {len(added_events)} 条，事件总数 {len(events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
