#!/usr/bin/env python3
"""重建 person_relation：删除违反规则的边、纠正方向、为每条边补写实质说明。

规则依据（AGENTS.md / docs/data-audit.md）：
- 皇帝不与文臣武将建立关系条目，仅保留宗室、家庭类关系；
- 人物库只收明代（含南明）人物，唐代杨氏实体混入须剔除；
- 每条关系应有出处可考的实质说明，不以“共事于某战事”这类机械共现充当关系。

用法：python3 rebuild_relations.py > 输出目录/person_relation.jsonl
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CONTENT = BACKEND / "data" / "content"

rels = [json.loads(l) for l in (CONTENT / "person_relation.jsonl").open(encoding="utf-8")]
people = [json.loads(l) for l in (CONTENT / "person.jsonl").open(encoding="utf-8")]
pby = {p["id"]: p for p in people}
emp = {pid for pid, p in pby.items() if p.get("category") == "帝王"}


def keep_edge(r: dict) -> bool:
    f = pby[r["from_person_id"]]
    t = pby[r["to_person_id"]]
    if r["relation_type"] in ("君臣", "政争", "统属"):
        other = r["to_person_id"] if r["from_person_id"] in emp else r["from_person_id"]
        if (r["from_person_id"] in emp or r["to_person_id"] in emp) and pby[other]["category"] in ("朝臣", "将帅", "内廷"):
            return False
    if r["from_person_id"] == "liuren" and r["to_person_id"] == "liujing":
        return False  # 刘讱之父刘璟（嘉靖刑部尚书）与刘基之子刘璟为两人
    if r["from_person_id"] == "yuanzongdao" and r["to_person_id"] == "yuanyingtai":
        return False  # 凤翔袁应泰与公安袁宗道无亲属关系
    if "yangshi" in (r["from_person_id"], r["to_person_id"]):
        return False  # 库内 yangshi 实为唐代虢国夫人，非包节之母
    if r["relation_type"] == "父子" and r["from_person_id"] == "mahuanghou" and r["to_person_id"] == "zhudi":
        return False  # 马皇后非父，母子边已表达
    if r["from_person_id"] == "zhuyijun" and r["to_person_id"] in ("zhuyoujian", "zhuyouxiao") and r["relation_type"] == "父子":
        return False  # 万历与天启、崇祯为祖孙，非父子
    return True


keep = [r for r in rels if keep_edge(r)]

# 事件池过滤（用户规则）：关系双方都必须是事件参与者。
_ep_rows = [json.loads(l) for l in (CONTENT / "event_participant.jsonl").open(encoding="utf-8")]
_participant_ids = {row["person_id"] for row in _ep_rows}
keep = [
    r for r in keep
    if r["from_person_id"] in _participant_ids and r["to_person_id"] in _participant_ids
]

# 方向纠正：统一为长辈->晚辈、长兄->幼弟。
FLIPS = {
    ("jianglong", "jiangang"): ("jiangang", "jianglong"),  # 姜昂(父)->姜龙
    ("zhanghongzhi", "zhangbi"): ("zhangbi", "zhanghongzhi"),  # 张弼(父)->张弘至
    ("wangxiangchun", "wangxiangqian"): ("wangxiangqian", "wangxiangchun"),  # 王象乾(兄)->王象春
    ("yuanzhongdao", "yuanhongdao"): ("yuanhongdao", "yuanzhongdao"),  # 袁宏道(兄)->袁中道
    ("yuanhongdao", "yuanzongdao"): ("yuanzongdao", "yuanhongdao"),  # 袁宗道(兄)->袁宏道
    ("lirubai", "lirusong"): ("lirusong", "lirubai"),  # 李如松(兄)->李如柏
    ("wangshizhen", "wangyu"): ("wangyu", "wangshizhen"),  # 王忬(父)->王世贞
}
for r in keep:
    key = (r["from_person_id"], r["to_person_id"])
    if key in FLIPS:
        r["from_person_id"], r["to_person_id"] = FLIPS[key]

# 去重：同一无序对只保留一条，父子边保留父->子方向。
canon: dict[frozenset, dict] = {}
for r in keep:
    key = frozenset([r["from_person_id"], r["to_person_id"]])
    if key not in canon:
        canon[key] = r
        continue
    prev = canon[key]

    def score(e: dict) -> int:
        return 10 if (e.get("note") or "").strip() else 0

    def prefer(e1: dict, e2: dict) -> dict:
        if e1["relation_type"] == "父子" and e2["relation_type"] == "父子":
            def birth(pid: str) -> int:
                m = re.match(r"(\d{4})", pby[pid]["years"] or "")
                return int(m.group(1)) if m else 0
            b1, b2 = birth(e1["from_person_id"]), birth(e2["from_person_id"])
            if b1 and b2 and b1 != b2:
                return e1 if b1 < b2 else e2
        return e1 if score(e1) >= score(e2) else e2

    canon[key] = prefer(prev, r)

final = list(canon.values())

# 每条边的实质说明：缺失或机械共现的 note 全部替换为有出处可考的叙述。
NOTES = {
    # ===== 父子·帝王世系 =====
    ("zhuyuanzhang", "zhubiao"): "朱标为太祖长子，洪武元年立为皇太子，监国十余年，洪武二十五年病逝，谥懿文。",
    ("zhuyuanzhang", "zhudi"): "朱棣为太祖第四子，初封燕王，建文四年靖难入继大统，是为成祖。",
    ("zhuyuanzhang", "zhuquan"): "朱权为太祖第十七子，封宁王，靖难时为朱棣所挟，后改封南昌。",
    ("zhuyuanzhang", "zhushuang"): "朱樉为太祖次子，封秦王，藩邸西安，洪武二十八年薨。",
    ("zhuyuanzhang", "zhusu"): "朱橚为太祖第五子，初封吴王，后改封周王，博学工词，藩邸开封。",
    ("zhubiao", "zhuyunwen"): "朱允炆为懿文太子次子，朱标早逝后受太祖册立为皇太孙，建文元年即位。",
    ("zhudi", "zhugaochi"): "朱高炽为成祖长子，永乐二十二年即位，是为仁宗，在位仅十个月。",
    ("zhudi", "zhugaoxu"): "朱高煦为成祖次子，靖难中为燕军主将，封汉王，宣德元年谋反被讨灭。",
    ("zhugaochi", "zhuzhanji"): "朱瞻基为仁宗长子，洪熙元年即位，是为宣宗。",
    ("zhuzhanji", "zhuqizhen"): "朱祁镇为宣宗长子，宣德十年即位，是为英宗，先后两度在位。",
    ("zhuzhanji", "zhuqiyu"): "朱祁钰为宣宗次子，土木之变后奉太后命监国即位，是为景帝。",
    ("zhuqizhen", "zhujian"): "朱见深为英宗长子，天顺八年即位，是为宪宗。",
    ("zhuqizhen", "zhujianze"): "朱见泽为英宗第六子，封德王，藩邸济南。",
    ("zhujian", "zhuyoutang"): "朱祐樘为宪宗第三子，成化二十三年即位，是为孝宗。",
    ("zhuyoutang", "zhuhouzhao"): "朱厚照为孝宗独子，弘治十八年即位，是为武宗。",
    ("zhuhoucong", "zhuzaihou"): "朱载坖为世宗第三子，嘉靖四十五年即位，是为穆宗。",
    ("zhuzaihou", "zhuyijun"): "朱翊钧为穆宗第三子，隆庆六年即位，是为神宗。",
    ("zhuyijun", "zhuchangluo"): "朱常洛为神宗长子，万历四十八年即位，是为光宗，在位月余而崩。",
    ("zhuchangluo", "zhuyouxiao"): "朱由校为光宗长子，泰昌元年即位，是为熹宗。",
    ("zhuchangluo", "zhuyoujian"): "朱由检为光宗第五子，天启七年即位，是为思宗。",
    ("zhushuang", "zhushangbing"): "朱尚炳为秦愍王朱樉长子，袭封秦王。",
    # ===== 母子 / 配偶 =====
    ("mahuanghou", "zhudi"): "马皇后为太祖正后，视诸皇子如己出，朱棣以嫡子名分受封燕王。",
    ("lixuanshi", "zhuyoumo"): "李选侍为光宗选侍，朱由模为光宗次子，早夭，追封简怀王。",
    ("mahuanghou", "zhuyuanzhang"): "马皇后为太祖嫡配，佐太祖定天下，以贤德著称，洪武十五年崩。",
    # ===== 父子·将相家世 =====
    ("hewenyuan", "heqiaoxin"): "何乔新为何文渊之子，父子皆登进士，何乔新官至刑部尚书。",
    ("huangzunsu", "huangzongxi"): "黄宗羲为黄尊素长子，尊素为东林名臣，死于阉祸，宗羲入清不仕，以遗民终。",
    ("lichengliang", "lirubai"): "李如柏为李成梁第三子，万历间任辽东总兵官，萨尔浒之战为南路军主将。",
    ("wangyu", "wangshizhen"): "王世贞为王忬长子，忬坐严嵩构陷被杀，世贞弃官持丧，后成文坛领袖。",
    ("yangtinghe", "yangshen"): "杨慎为杨廷和长子，正德六年状元，大礼议中受廷杖戍云南永昌卫。",
    ("zhangyu", "zhangfu"): "张辅为张玉长子，玉战死东昌，辅袭爵，历事五朝，土木之变殉国。",
    ("zhouxuan", "zhoujing"): "周经为周瑄长子，父子皆官至尚书，周经以清介著称。",
    ("xiayunyi", "xiawanchun"): "夏完淳为夏允彝之子，父子皆为抗清志士，完淳十七岁殉国。",
    ("lichengliang", "lirusong"): "李如松为李成梁长子，袭宁远伯，万历间平定宁夏、援朝抗倭。",
    ("changyuchun", "changmao"): "常茂为常遇春长子，袭郑国公，后坐事安置龙州。",
    ("changyuchun", "changsheng"): "常升为常遇春次子，袭开国公，建文末殉国。",
    ("liuji", "liujing"): "刘璟为刘基次子，任阁门使，靖难时抗节不屈，自经死。",
    ("liuji", "liulian"): "刘琏为刘基长子，仕至江西右参政，为胡惟庸党所陷，堕井死。",
    ("liwenzhong", "lijinglong"): "李景隆为李文忠长子，袭曹国公，建文时拜大将军北伐，兵败降燕。",
    ("liwenzhong", "lizengzhi"): "李增枝为李文忠次子，官至前军左都督，永乐初坐景隆事夺爵。",
    ("musheng", "mubin"): "沐斌为沐晟之子，袭黔国公，镇守云南。",
    ("muying", "muchun"): "沐春为沐英长子，袭西平侯，镇云南，洪武末卒于任。",
    ("muying", "musheng"): "沐晟为沐英次子，袭西平侯，后进黔国公，永乐间征交阯。",
    ("shenshixing", "shenyongmao"): "申用懋为申时行之子，父子皆入阁，用懋官至兵部侍郎。",
    ("xuda", "xuhuizu"): "徐辉祖为徐达长子，袭魏国公，靖难时忠于建文，被削爵禁锢。",
    ("xuda", "xuyingxu"): "徐膺绪为徐达第三子，官中军都督佥事，成祖朝掌中都留守司。",
    ("xuda", "xuzengshou"): "徐增寿为徐达第四子，暗中通燕，被建文帝诛杀，后追封定国公。",
    ("zhengzhilong", "zhengchenggong"): "郑成功为郑芝龙之子，芝龙降清后成功举兵海上，奉明正朔抗清。",
    ("caowenzhao", "caobianjiao"): "曹变蛟为曹文诏从子，骁勇冠诸军，松山之战力战死。",
    ("jiangang", "jianglong"): "姜龙为姜昂之子，父子皆登进士，姜龙官至云南按察副使。",
    ("zhangbi", "zhanghongzhi"): "张弘至为张弼之子，弼以书名，弘至官至南安知府。",
    # ===== 兄弟姐妹 =====
    ("zhuqiyu", "zhuqizhen"): "朱祁钰与朱祁镇同为宣宗之子，英宗北狩后景帝即位，兄弟因皇位反目。",
    ("zhuyoujian", "zhuyouxiao"): "朱由检为朱由校之弟，熹宗无嗣，以信王入继大统。",
    ("zhugaochi", "zhugaoxu"): "朱高煦为朱高炽同母弟，靖难有功，后谋夺嫡，宣德元年伏诛。",
    ("zhudi", "zhuquan"): "朱权为朱棣第十七弟，靖难时被挟持入燕军，事成后改封南昌。",
    ("lirusong", "lirubai"): "李如柏为李如松之弟，如松战殁后如柏代为辽东总兵。",
    ("wangxiangqian", "wangxiangchun"): "王象春为王象乾之弟，新城王氏兄弟皆显宦，象春以诗名。",
    ("yuanzongdao", "yuanhongdao"): "袁宏道为袁宗道之弟，兄弟三人并称公安三袁，倡性灵说。",
    ("yuanzongdao", "yuanzhongdao"): "袁中道为袁宗道之弟，公安派殿军，著有《珂雪斋集》。",
    ("yuanhongdao", "yuanzhongdao"): "袁中道为袁宏道之弟，兄弟皆以诗文名于万历文坛。",
    ("zhuyipai", "zhuyihai"): "朱以海为朱以派之弟，鲁王以派被清军所杀后，以海嗣鲁王监国。",
    # ===== 同僚（改写机械共现 note） =====
    ("changyuchun", "xuda"): "常遇春与徐达并为开国名将，洪武元年会师北伐，共克大都。",
    ("chenlin", "dengzilong"): "陈璘与邓子龙同率水师援朝，万历二十六年露梁海战中并肩作战，邓子龙战殁。",
    ("chenlin", "magui"): "陈璘统水军、麻贵统陆军，万历援朝之役中水陆并进，协同作战。",
    ("dengzilong", "magui"): "邓子龙与麻贵同隶援朝明军，分任水陆主将，露梁海战同役。",
    ("fuyoude", "lanyu"): "傅友德与蓝玉同征云南，洪武十四年分道进兵，会克昆明。",
    ("fuyoude", "muying"): "傅友德与沐英同征云南，事定后沐英留镇，傅友德班师。",
    ("lanyu", "muying"): "蓝玉与沐英同征云南，蓝玉为前锋，沐英破大理。",
    ("gaopanlong", "zouyuanbiao"): "高攀龙与邹元标同列东林名臣，以讲学议政相砥砺。",
    ("guxiancheng", "gaopanlong"): "顾宪成与高攀龙先后主盟东林书院，以清议左右万历朝政。",
    ("huanghuai", "yangpu"): "黄淮与杨溥同为永乐至宣德间内阁重臣，历事三朝。",
    ("huweyong", "lishanchang"): "李善长晚年与胡惟庸结姻亲，胡惟庸案发后李善长坐罪赐死。",
    ("huweyong", "chenning"): "陈宁为胡惟庸党羽，官至左都御史，洪武十三年坐胡案族诛。",
    ("lirusong", "magui"): "李如松与麻贵同征宁夏、援朝鲜，万历二十年并肩作战。",
    ("lirusong", "dongyiyuan"): "李如松与董一元同属援朝明军，分路进兵朝鲜。",
    ("lidongyang", "liujian"): "李东阳与刘健同在内阁，弘治朝并称贤相，正德初同受刘瑾排挤。",
    ("lidongyang", "xieqian"): "李东阳与谢迁同在内阁，弘治朝共理朝政，正德初同遭排挤。",
    ("liujian", "xieqian"): "刘健与谢迁同为弘治阁臣，正德初乞休，与李东阳并称三老。",
    ("magui", "dongyiyuan"): "麻贵与董一元同属万历援朝明军，分统北路与中路。",
    ("qijiguang", "tanlun"): "谭纶经略东南，荐戚继光总理蓟州军务，两人合力练兵御倭。",
    ("qijiguang", "yudayou"): "戚继光与俞大猷并称抗倭名将，先后经营东南海防。",
    ("qitai", "huangzicheng"): "齐泰与黄子澄同受建文帝倚信，共谋削藩，燕兵南下后同被族诛。",
    ("shengyong", "tiexuan"): "盛庸与铁铉同守济南，屡挫燕军，建文四年后铁铉被擒不屈死。",
    ("shenli", "guozhengyu"): "沈鲤与郭正域同为东林党人，妖书案中同被牵连。",
    ("wangji", "mubin"): "王骥总督军务征麓川，沐斌以云南总兵官率兵协剿。",
    ("wangzhi-minister", "chenxun"): "王直与陈循同列景泰朝内阁，共主中枢。",
    ("xuda", "tanghe"): "徐达与汤和同里起兵，从太祖征战，并为开国六王。",
    ("xuda", "fengsheng"): "徐达与冯胜并为开国元勋，北伐时冯胜从徐达进兵。",
    ("xuda", "muying"): "徐达与沐英俱为太祖养子，开国战争中同受驱策。",
    ("yanglian", "zuoguangdou"): "杨涟与左光斗同列东林，移宫案中共持正论，天启间同死于阉祸。",
    ("yanglian-2", "zhaonanxing"): "杨涟与赵南星同属东林党，天启间同被魏忠贤党诬陷。",
    ("yangshiqi", "yangrong"): "杨士奇与杨荣并称三杨，历仕永乐、洪熙、宣德、正统四朝内阁。",
    ("yangtinghe", "maocheng"): "毛澄依杨廷和之意拟定世宗入继大统礼仪，后因议礼不合告退。",
    ("yuanchonghuan", "mangui"): "袁崇焕与满桂同在己巳之变中入卫京师，因军务龃龉，满桂出战死。",
    ("yuqian", "wangzhi"): "于谦与王直同列景泰朝中枢，王直荐于谦任兵部尚书。",
    ("zhangcong", "guie"): "张璁与桂萼同为议礼派核心，借大礼议骤贵。",
    ("zhangcong", "xishu"): "席书率先上疏附和张璁议礼主张，官至礼部尚书。",
    ("zhangcong", "huotao"): "霍韬与张璁同倡大礼议，嘉靖朝同列显宦。",
    ("zhanghuangyan", "zhengchenggong"): "张煌言与郑成功联兵北伐，永历十三年会师入长江，功败垂成。",
    ("zhangjuzheng", "fengbao"): "张居正与司礼监掌印冯保内外相结，共辅幼主，推行万历新政。",
    ("zhugeng", "shenyiguan"): "朱赓与沈一贯同在内阁，妖书案中同被言官弹劾。",
    ("zudashou", "wusangui"): "祖大寿与吴三桂为舅甥，同守辽西，松锦战后祖大寿降清。",
    ("shenshixing", "zhangjuzheng"): "申时行与张居正同在内阁，张居正为万历首辅，申时行继其位。",
    ("yansong", "wangyu"): "严嵩把持内阁，罗织罪名构陷蓟辽总督王忬，王忬下狱处决，后得平反。",
    # ===== 统属 =====
    ("chenlin", "wuweizhong"): "吴惟忠为陈璘部将，随征朝鲜，露梁海战中隶陈璘水军。",
    ("hongchengchou", "zudashou"): "洪承畴总督蓟辽，松锦之战中祖大寿守锦州，城破后降清。",
    ("hongchengchou", "wusangui"): "吴三桂为松锦八总兵之一，隶洪承畴麾下，后为山海关总兵。",
    ("hongchengchou", "caobianjiao"): "曹变蛟为松锦八总兵之一，松山突围时力战死。",
    ("lijinglong", "gengbingwen"): "李景隆代耿炳文为北伐主帅，耿炳文以老将坐镇，兵败后罢。",
    ("sunchengzong", "mashilong"): "马世龙为孙承宗部将，孙承宗再督辽时复起用之。",
    ("sunchengzong", "mangui"): "满桂受孙承宗调度，任山海关总兵，守辽有功。",
    ("sunchengzong", "zudashou"): "孙承宗督师收复遵永四城，祖大寿时为部将，大凌河之役后降清。",
    ("wangji", "jianggui"): "王骥总督军务，蒋贵为总兵官，正统间三征麓川。",
    ("wangji-2", "wangzhen"): "王骥奉司礼监王振意旨力主征麓川，以媚王振。",
    ("wangshouren", "wuwending"): "王守仁巡抚南赣、提督军务，伍文定为部将，从平宸濠之乱。",
    ("weizhongxian", "weiguangwei"): "魏广微依附魏忠贤，入阁拜相，为阉党要员。",
    ("yanghao", "lirubai"): "杨镐经略辽东，四路出师攻后金，李如柏领南路军。",
    ("yanghao", "lirusong"): "李如松为辽东总兵时受杨镐节制，萨尔浒前卒。",
    ("yanghao", "wangxuan"): "王宣为西路杜松所部总兵，萨尔浒之战中路先溃。",
    ("yangyiqing", "qiuyue"): "杨一清总制陕西军务，仇钺为部将，平寘鐇之乱。",
    ("yuanchonghuan", "sunchengzong"): "孙承宗经略辽东，袁崇焕为其所识拔，后继任督师。",
    ("yuanchonghuan", "zudashou"): "祖大寿为袁崇焕麾下大将，袁崇焕下狱后祖大寿一度东走。",
    ("yuanchonghuan", "zhaolvjiao"): "赵率教为袁崇焕部将，己巳之变中战死遵化。",
    ("yuqian", "shiheng"): "于谦主持京师防务，石亨为京师总兵官，德胜门之战却敌。",
    # ===== 政争 =====
    ("liujin", "zhuzhenfan"): "朱寘鐇以讨刘瑾为名起兵宁夏，旋败，事连刘瑾擅权。",
    ("shenyiguan", "weizhongxian"): "沈一贯结浙党，其后阉党魏忠贤势起，两党相继与东林对立。",
    ("shenyiguan", "gaopanlong"): "沈一贯为浙党领袖，与东林党人高攀龙等相攻讦。",
    ("weizhongxian", "yanglian"): "魏忠贤与东林党杨涟对立，杨涟劾其二十四大罪，反被构陷致死。",
    ("weizhongxian", "zuoguangdou"): "魏忠贤党羽迫害东林党人左光斗，左光斗死于诏狱。",
    ("yangtinghe", "zhangcong"): "杨廷和与张璁在大礼议中针锋相对，张璁议礼得胜，杨廷和致仕。",
    ("zhuzhanji", "zhugaoxu"): "宣德元年朱高煦据乐安谋反，宣宗亲征讨平，废为庶人。",
    # ===== 师承 =====
    ("sunyuanhua", "xuguangqi"): "孙元化师从徐光启，受其荐举，两人皆精西洋火器之学。",
}

# 事件池内名人的新关系边（原数据缺失，直接补建）
EXTRA_EDGES = [
    {"from_person_id": "shenshixing", "to_person_id": "zhangjuzheng",
     "relation_type": "同僚", "reign": "万历", "source_id": "mingshi-editorial-v1",
     "note": "申时行与张居正同在内阁，张居正为万历首辅，申时行继其位。"},
    {"from_person_id": "yansong", "to_person_id": "wangyu",
     "relation_type": "政争", "reign": "嘉靖", "source_id": "mingshi-editorial-v1",
     "note": "严嵩把持内阁，罗织罪名构陷蓟辽总督王忬，王忬下狱处决，后得平反。"},
    {"from_person_id": "xuda", "to_person_id": "xuyingxu",
     "relation_type": "父子", "reign": "洪武、永乐", "source_id": "mingshi-editorial-v1",
     "note": "徐膺绪为徐达第三子，官中军都督佥事，成祖朝掌中都留守司。"},
]

out = []
missing = []
for r in final:
    key = (r["from_person_id"], r["to_person_id"])
    note = NOTES.get(key)
    if note is not None:
        r["note"] = note
    elif not (r.get("note") or "").strip():
        missing.append(key)
    out.append(r)

existing_pairs = {frozenset([r["from_person_id"], r["to_person_id"]]) for r in out}
for extra in EXTRA_EDGES:
    pair = frozenset([extra["from_person_id"], extra["to_person_id"]])
    if pair not in existing_pairs:
        out.append(extra)
        existing_pairs.add(pair)

# 输出字段保持库格式：id 由数据库自增，JSONL 不写 id。
if missing:
    raise SystemExit(f"MISSING NOTES: {missing}")

out.sort(key=lambda r: (r["relation_type"], r["from_person_id"], r["to_person_id"]))
print(f"# rebuilt person_relation: {len(out)} edges")
for r in out:
    print(json.dumps(r, ensure_ascii=False))


# ---- 同步 catalog.py 种子 -------------
# 服务启动时 catalog 同步会按 RELATIONS 逐条 upsert 关系，且不删除库中多余边；
# 因此 RELATIONS 必须与重建后内容完全一致，否则旧边会在下次启动回填。
def emit_catalog_relations() -> str:
    lines = ["RELATIONS = ["]
    for r in out:
        lines.append(
            f'    ({r["from_person_id"]!r}, {r["to_person_id"]!r}, {r["relation_type"]!r}, {r["reign"]!r}, {r["note"]!r}),'
        )
    lines.append("]")
    return "\n".join(lines)


if __name__ == "__main__" and "--catalog" in __import__("sys").argv:
    import re as _re

    catalog_path = BACKEND / "app" / "catalog.py"
    catalog = catalog_path.read_text(encoding="utf-8")
    new_block = emit_catalog_relations()
    pattern = _re.compile(r"RELATIONS = \[.*?\]", _re.S)
    updated, n = pattern.subn(lambda m: new_block, catalog, count=1)
    assert n == 1, "RELATIONS block not found in catalog.py"
    catalog_path.write_text(updated, encoding="utf-8")
    print(f"catalog.py RELATIONS replaced with {len(out)} entries")
