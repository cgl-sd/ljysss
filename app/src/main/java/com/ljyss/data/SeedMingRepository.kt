package com.ljyss.data

import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.MapLayer
import com.ljyss.data.model.MapLabel
import com.ljyss.data.model.MapLabelAnchor
import com.ljyss.data.model.MapPeriod
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.RelationshipType
import com.ljyss.data.model.Institution
import com.ljyss.data.model.InstitutionReform
import com.ljyss.data.model.Reign
import com.ljyss.data.model.SpecialItem

/**
 * 仅用于首版界面演示。正式资料将由后端按来源、时间和地理范围维护。
 */
object SeedMingRepository : MingRepository {
    private const val MingShilu = "《明实录》资料索引"
    // 离线演示与内容服务采用同一年的粒度，避免把一个年号内相距数十年的事件混在同一页。
    private val seedEventYears = mapOf(
        "定国号，建元“洪武”" to 1368,
        "元顺帝北走上都" to 1368,
        "明军进入大都" to 1368,
        "改大都为北平府" to 1368,
        "定应天为南京" to 1368,
        "卫所制度初定" to 1368,
        "建文改元" to 1399,
        "削藩议政" to 1399,
        "永乐改元" to 1403,
        "北平改顺天府" to 1403,
        "洪熙改元" to 1425,
        "宣德改元" to 1426,
        "安南善后" to 1428,
        "正统改元" to 1436,
        "北边军情" to 1449,
        "景泰改元" to 1450,
        "天顺改元" to 1457,
        "成化改元" to 1465,
        "弘治改元" to 1488,
        "正德改元" to 1506,
        "嘉靖改元" to 1522,
        "东南海防" to 1555,
        "隆庆改元" to 1567,
        "万历改元" to 1573,
        "考成法推行" to 1573,
        "泰昌改元" to 1620,
        "天启改元" to 1621,
        "崇祯改元" to 1628,
        "京师军情" to 1644,
    )

    /**
     * 年号索引已覆盖明朝全部十七个年号；正式事件按年、月从 API 增量加载。
     * 这里的事件是可运行的首批样本，而不是把完整史料硬编码在 UI 中。
     */
    private val reignData = listOf(
        Reign("洪武", "1368—1398", "洪武元年 · 1368", "大明肇建，定都应天府。", listOf(
            HistoricalEvent("正月", "定国号，建元“洪武”", "朱元璋即皇帝位，国号大明，开启洪武纪年。", "应天府", MingShilu),
            HistoricalEvent("七月", "元顺帝北走上都", "明军北进后，元顺帝离开大都北走上都，元廷统治中心随之北移。", "大都—上都", MingShilu),
            HistoricalEvent("八月", "明军进入大都", "徐达率北伐军进入元大都，明军取得北方战略要地。", "大都", MingShilu),
            HistoricalEvent("八月", "改大都为北平府", "明廷诏改大都路为北平府，北方政治空间进入新的行政格局。", "北平府", MingShilu),
            HistoricalEvent("八月", "定应天为南京", "应天府建为南京，明初两京格局由此展开。", "南京", MingShilu),
            HistoricalEvent("是年", "卫所制度初定", "明廷在建国与北伐并行的背景下编定卫所，军政组织逐步制度化。", "应天府", MingShilu),
        )),
        Reign("建文", "1399—1402", "建文元年 · 1399", "削藩与靖难，王朝的第一次大转折。", listOf(
            HistoricalEvent("正月", "建文改元", "朱允炆继统，朝廷由此启用建文年号。", "南京", MingShilu),
            HistoricalEvent("四月", "削藩议政", "中央与诸藩的关系成为朝廷政务的重要议题。", "南京", MingShilu),
        )),
        Reign("永乐", "1403—1424", "永乐元年 · 1403", "迁都北京、修《永乐大典》与海上交流共同塑造这一时期。", listOf(
            HistoricalEvent("正月", "永乐改元", "朱棣即位后改元永乐，朝廷仍在南京处理政务。", "南京", MingShilu),
            HistoricalEvent("二月", "北平改顺天府", "北方政治中心的营建由此展开。", "顺天府", MingShilu),
        )),
        Reign("洪熙", "1425", "洪熙元年 · 1425", "短暂的一年，朝政由永乐末年的动员转向休养与整饬。", listOf(
            HistoricalEvent("正月", "洪熙改元", "朱高炽即位，启用洪熙年号。", "北京", MingShilu),
        )),
        Reign("宣德", "1426—1435", "宣德元年 · 1426", "守成之世，边政与内治并举。", listOf(
            HistoricalEvent("正月", "宣德改元", "朱瞻基即位，承续前朝制度。", "北京", MingShilu),
            HistoricalEvent("六月", "安南善后", "西南边境政局调整，朝廷重新评估治理方式。", "交趾", MingShilu),
        )),
        Reign("正统", "1436—1449", "正统元年 · 1436", "英宗初政，北边压力渐增。", listOf(
            HistoricalEvent("正月", "正统改元", "明英宗以正统为年号。", "北京", MingShilu),
            HistoricalEvent("七月", "北边军情", "边防与军政成为朝廷持续关切。", "大同", MingShilu),
        )),
        Reign("景泰", "1450—1457", "景泰元年 · 1450", "北京保卫战后，国家在危局中重整军政。", listOf(
            HistoricalEvent("正月", "景泰改元", "郕王朱祁钰即位，改元景泰。", "北京", MingShilu),
        )),
        Reign("天顺", "1457—1464", "天顺元年 · 1457", "英宗复辟，朝局再次转向。", listOf(
            HistoricalEvent("正月", "天顺改元", "英宗复位，改元天顺。", "北京", MingShilu),
        )),
        Reign("成化", "1465—1487", "成化元年 · 1465", "中期制度与地方治理持续展开。", listOf(
            HistoricalEvent("正月", "成化改元", "宪宗即位，启用成化年号。", "北京", MingShilu),
        )),
        Reign("弘治", "1488—1505", "弘治元年 · 1488", "朝廷着力整饬政务，形成中期的重要治理阶段。", listOf(
            HistoricalEvent("正月", "弘治改元", "孝宗即位，启用弘治年号。", "北京", MingShilu),
        )),
        Reign("正德", "1506—1521", "正德元年 · 1506", "内廷、边事与地方军事活动交织。", listOf(
            HistoricalEvent("正月", "正德改元", "武宗即位，启用正德年号。", "北京", MingShilu),
        )),
        Reign("嘉靖", "1522—1566", "嘉靖元年 · 1522", "礼制议题、东南海防与财政困局交织。", listOf(
            HistoricalEvent("正月", "嘉靖改元", "世宗即位，朝局进入新的阶段。", "北京", MingShilu),
            HistoricalEvent("五月", "东南海防", "沿海军民共同面对海上威胁。", "浙江", MingShilu),
        )),
        Reign("隆庆", "1567—1572", "隆庆元年 · 1567", "朝廷重议边政、海贸与财政问题。", listOf(
            HistoricalEvent("正月", "隆庆改元", "穆宗即位，启用隆庆年号。", "北京", MingShilu),
        )),
        Reign("万历", "1573—1620", "万历元年 · 1573", "改革、援朝与辽东局势共同塑造晚明。", listOf(
            HistoricalEvent("正月", "万历改元", "神宗即位，张居正继续主持政务。", "北京", MingShilu),
            HistoricalEvent("四月", "考成法推行", "吏治与财政整饬成为朝廷关注重点。", "北京", MingShilu),
        )),
        Reign("泰昌", "1620", "泰昌元年 · 1620", "政局转换极为迅速的一年。", listOf(
            HistoricalEvent("八月", "泰昌改元", "光宗即位，启用泰昌年号。", "北京", MingShilu),
        )),
        Reign("天启", "1621—1627", "天启元年 · 1621", "辽东局势与朝廷内政相互牵动。", listOf(
            HistoricalEvent("正月", "天启改元", "熹宗即位，启用天启年号。", "北京", MingShilu),
        )),
        Reign("崇祯", "1628—1644", "崇祯元年 · 1628", "内外交困，王朝走向终局。", listOf(
            HistoricalEvent("正月", "崇祯改元", "思宗即位，力图整饬积弊。", "北京", MingShilu),
            HistoricalEvent("三月", "京师军情", "北方局势愈发紧迫。", "京师", MingShilu),
        )),
    )

    private val peopleData = listOf(
        HistoricalPerson("朱元璋", "明太祖 · 洪武帝", "洪武", "1328—1398", "起于淮右，建立大明，定都应天。", PersonCategory.EMPERORS),
        HistoricalPerson("朱允炆", "明惠帝 · 建文帝", "建文", "1377—1402", "削藩改制，靖难之变后下落成为明代史的重要悬案。", PersonCategory.EMPERORS),
        HistoricalPerson("朱棣", "明成祖 · 永乐帝", "永乐", "1360—1424", "迁都北京，经营北方，命郑和下西洋。", PersonCategory.EMPERORS),
        HistoricalPerson("朱高炽", "明仁宗 · 洪熙帝", "洪熙", "1378—1425", "在位虽短，以宽政与息兵调整永乐时期的国家动员。", PersonCategory.EMPERORS),
        HistoricalPerson("朱瞻基", "明宣宗 · 宣德帝", "宣德", "1399—1435", "在位十年，承续仁宣之治。", PersonCategory.EMPERORS),
        HistoricalPerson("朱祁镇", "明英宗 · 正统帝 / 天顺帝", "正统、天顺", "1427—1464", "土木之变与复辟使其一生横跨明代两次重大政局转折。", PersonCategory.EMPERORS),
        HistoricalPerson("朱祁钰", "明代宗 · 景泰帝", "景泰", "1428—1457", "土木之变后即位，任用于谦守卫北京并重整军政。", PersonCategory.EMPERORS),
        HistoricalPerson("朱见深", "明宪宗 · 成化帝", "成化", "1447—1487", "成化年间整饬边防，宫廷与地方社会均发生持续变化。", PersonCategory.EMPERORS),
        HistoricalPerson("朱祐樘", "明孝宗 · 弘治帝", "弘治", "1470—1505", "以勤政和宽厚著称，形成弘治中兴的政治形象。", PersonCategory.EMPERORS),
        HistoricalPerson("朱厚照", "明武宗 · 正德帝", "正德", "1491—1521", "内廷与边事交织，正德朝呈现强烈的个人统治色彩。", PersonCategory.EMPERORS),
        HistoricalPerson("朱厚熜", "明世宗 · 嘉靖帝", "嘉靖", "1507—1567", "大礼议后长期在位，嘉靖时期礼制、海防与财政并行。", PersonCategory.EMPERORS),
        HistoricalPerson("朱载坖", "明穆宗 · 隆庆帝", "隆庆", "1537—1572", "在位期间调整北方边政并推动海贸政策变化。", PersonCategory.EMPERORS),
        HistoricalPerson("朱翊钧", "明神宗 · 万历帝", "万历", "1563—1620", "万历年间改革、援朝与辽东局势共同塑造晚明。", PersonCategory.EMPERORS),
        HistoricalPerson("朱常洛", "明光宗 · 泰昌帝", "泰昌", "1582—1620", "在位不足一月，泰昌朝成为晚明皇位更替的重要节点。", PersonCategory.EMPERORS),
        HistoricalPerson("朱由校", "明熹宗 · 天启帝", "天启", "1605—1627", "天启时期辽东战局与内廷政治彼此牵动。", PersonCategory.EMPERORS),
        HistoricalPerson("朱由检", "明思宗 · 崇祯帝", "崇祯", "1611—1644", "即位后试图整饬积弊，最终面对内外交困的王朝终局。", PersonCategory.EMPERORS),
        HistoricalPerson("刘基", "诚意伯", "洪武", "1311—1375", "辅佐朱元璋完成建国，兼具谋略家与文学家的身份。", PersonCategory.MINISTERS),
        HistoricalPerson("李文忠", "曹国公", "洪武", "1339—1384", "明初北伐与北方防务的重要统帅。", PersonCategory.GENERALS),
        HistoricalPerson("方孝孺", "翰林侍讲", "建文", "1357—1402", "建文朝文臣，因靖难之后的选择成为历史记忆中的刚直之士。", PersonCategory.LITERATI),
        HistoricalPerson("杨士奇", "内阁首辅", "永乐、洪熙、宣德", "1364—1444", "历仕三朝，参与形成仁宣时期的内阁政治。", PersonCategory.MINISTERS),
        HistoricalPerson("张居正", "内阁首辅", "万历", "1525—1582", "以考成法整饬吏治，主持万历初政。", PersonCategory.MINISTERS),
        HistoricalPerson("于谦", "兵部尚书", "正统", "1398—1457", "北京保卫战中的关键人物。", PersonCategory.MINISTERS),
        HistoricalPerson("海瑞", "右佥都御史", "嘉靖", "1514—1587", "以清直敢言著称。", PersonCategory.MINISTERS),
        HistoricalPerson("徐达", "魏国公", "洪武", "1332—1385", "明初北伐的重要统帅。", PersonCategory.GENERALS),
        HistoricalPerson("戚继光", "蓟州总兵官", "嘉靖", "1528—1588", "整练军伍，抗倭并经营北方边备。", PersonCategory.GENERALS),
        HistoricalPerson("李如松", "辽东总兵官", "万历", "1549—1598", "参与援朝战争，活跃于辽东与朝鲜。", PersonCategory.GENERALS),
        HistoricalPerson("袁崇焕", "蓟辽督师", "天启、崇祯", "1584—1630", "主持辽东防务，宁远战事与其身后评价成为晚明边政的重要议题。", PersonCategory.GENERALS),
        HistoricalPerson("王守仁", "思想家、军事家", "正德", "1472—1529", "心学代表人物，也曾参与平乱。", PersonCategory.LITERATI),
        HistoricalPerson("李梦阳", "文学家", "弘治、正德", "1473—1529", "前七子代表人物，主张复古以振兴文坛。", PersonCategory.LITERATI),
        HistoricalPerson("归有光", "散文家", "嘉靖", "1507—1571", "以平淡自然的古文见长。", PersonCategory.LITERATI),
        HistoricalPerson("徐渭", "文学家、书画家", "嘉靖", "1521—1593", "诗文、书画与戏曲评论兼擅，体现晚明文人的多重面貌。", PersonCategory.LITERATI),
        HistoricalPerson("汤显祖", "戏曲家", "万历", "1550—1616", "《牡丹亭》作者。", PersonCategory.LITERATI),
        HistoricalPerson("郑和", "内官监太监", "永乐", "1371—1433", "七下西洋，沟通东南亚与印度洋世界。", PersonCategory.COURT),
        HistoricalPerson("王振", "司礼监太监", "正统", "？—1449", "正统朝的重要宦官。", PersonCategory.COURT),
        HistoricalPerson("刘瑾", "司礼监太监", "正德", "1451—1510", "正德初年权势显赫，反映内廷权力对朝政的影响。", PersonCategory.COURT),
        HistoricalPerson("冯保", "司礼监太监", "万历", "？—1583", "与万历初年政局关系密切。", PersonCategory.COURT),
        HistoricalPerson("魏忠贤", "司礼监太监", "天启", "1568—1627", "天启年间内廷权力的代表人物，晚明政治史争议集中。", PersonCategory.COURT),
        // 后妃与藩王：离线种子至少覆盖每一类人物，保证断网时全部栏目可浏览。
        HistoricalPerson("马皇后", "明太祖皇后", "洪武", "1332—1382", "孝慈高皇后马氏，明太祖朱元璋的皇后，明初宫廷政治的重要参与者。", PersonCategory.COURT),
        HistoricalPerson("朱常洵", "福王", "万历", "1586—1641", "明神宗第三子，封福王；明末宗室中的重要人物。", PersonCategory.CLAN),
        // 名臣：首批扩展名录，卷次与引文位置由后端资料校对流程补全。
        HistoricalPerson("李善长", "韩国公", "洪武", "1314—1390", "明初开国功臣，长期参与制度草创与中枢政务。", PersonCategory.MINISTERS, courtesyName = "百室"),
        HistoricalPerson("宋濂", "翰林学士承旨", "洪武", "1310—1381", "明初重要文臣与学者，主持《元史》修纂并参与朝廷文教事务。", PersonCategory.MINISTERS, courtesyName = "景濂"),
        HistoricalPerson("胡惟庸", "左丞相", "洪武", "？—1380", "洪武朝丞相；其案及其后中书省废除，是明初中枢制度变化的重要节点。", PersonCategory.MINISTERS),
        HistoricalPerson("夏原吉", "户部尚书", "永乐、洪熙、宣德", "1366—1430", "长期掌理财政、漕运与水利，是永乐至宣德朝的重要理财官员。", PersonCategory.MINISTERS, courtesyName = "维喆"),
        HistoricalPerson("解缙", "翰林学士", "永乐", "1369—1415", "参与《永乐大典》修纂，亦以直言和政治际遇著称。", PersonCategory.MINISTERS, courtesyName = "大绅"),
        HistoricalPerson("杨荣", "少师", "永乐、洪熙、宣德", "1371—1440", "与杨士奇、杨溥并称“三杨”，参与仁宣时期内阁事务。", PersonCategory.MINISTERS, courtesyName = "勉仁"),
        HistoricalPerson("杨溥", "少保", "永乐、洪熙、宣德", "1372—1446", "仁宣朝内阁重臣，三杨之一。", PersonCategory.MINISTERS, courtesyName = "弘济"),
        HistoricalPerson("王直", "吏部尚书", "正统、景泰", "1379—1462", "历经英宗、代宗时期，在中枢政务与人事任用中任职。", PersonCategory.MINISTERS, courtesyName = "行俭"),
        HistoricalPerson("王翱", "吏部尚书", "景泰、天顺", "1384—1467", "景泰、天顺年间的重臣，以整饬吏治见称。", PersonCategory.MINISTERS, courtesyName = "九皋"),
        HistoricalPerson("李贤", "内阁首辅", "天顺、成化", "1409—1467", "天顺复辟后居中枢，参与成化初年的政务。", PersonCategory.MINISTERS, courtesyName = "原德"),
        HistoricalPerson("商辂", "吏部尚书、大学士", "成化", "1414—1486", "明代少有的连中三元者，成化朝曾入阁参预机务。", PersonCategory.MINISTERS, courtesyName = "弘载"),
        HistoricalPerson("刘健", "内阁首辅", "弘治", "1433—1526", "弘治朝内阁大臣，参与中期朝政。", PersonCategory.MINISTERS, courtesyName = "希贤"),
        HistoricalPerson("李东阳", "内阁首辅", "弘治、正德", "1447—1516", "弘治、正德之际的内阁重臣，兼具政治与文学影响。", PersonCategory.MINISTERS, courtesyName = "宾之"),
        HistoricalPerson("谢迁", "内阁大学士", "弘治、正德", "1449—1531", "弘治朝重臣，正德初与刘健、李东阳并称。", PersonCategory.MINISTERS, courtesyName = "于乔"),
        HistoricalPerson("杨廷和", "内阁首辅", "正德、嘉靖", "1459—1529", "正德末、嘉靖初主持中枢政务，大礼议前后是关键人物。", PersonCategory.MINISTERS, courtesyName = "介夫"),
        HistoricalPerson("严嵩", "内阁首辅", "嘉靖", "1480—1567", "嘉靖中后期长期居中枢，相关政治评价需结合不同史料阅读。", PersonCategory.MINISTERS, courtesyName = "惟中"),
        HistoricalPerson("徐阶", "内阁首辅", "嘉靖、隆庆", "1503—1583", "嘉靖末入阁，后在隆庆初政中仍具影响。", PersonCategory.MINISTERS, courtesyName = "子升"),
        HistoricalPerson("高拱", "内阁首辅", "隆庆、万历", "1513—1578", "隆庆、万历之际的中枢大臣，与张居正同为晚明制度转折的相关人物。", PersonCategory.MINISTERS, courtesyName = "肃卿"),
        HistoricalPerson("申时行", "内阁首辅", "万历", "1535—1614", "万历前期主持内阁事务，经历张居正去世后的中枢调整。", PersonCategory.MINISTERS, courtesyName = "汝默"),
        HistoricalPerson("叶向高", "内阁首辅", "万历、泰昌、天启", "1559—1627", "晚明内阁重臣，长期面对党争、财政与边防问题。", PersonCategory.MINISTERS, courtesyName = "进卿"),
        HistoricalPerson("孙承宗", "兵部尚书、大学士", "天启", "1563—1638", "主持辽东经略，兼具中枢与边防经验。", PersonCategory.MINISTERS, courtesyName = "稚绳"),
        HistoricalPerson("史可法", "兵部尚书", "崇祯、弘光", "1601—1645", "明末官员，崇祯末至南明初的政治与军事活动常被并置讨论。", PersonCategory.MINISTERS, courtesyName = "宪之"),
        // 武将：按明初、海防、边镇和晚明战局分期收录。
        HistoricalPerson("常遇春", "鄂国公", "洪武", "1330—1369", "明初开国将领，参与平定江南与北伐。", PersonCategory.GENERALS),
        HistoricalPerson("蓝玉", "凉国公", "洪武", "？—1393", "洪武后期名将，北方军事活动与其后案件均是明初史的重要议题。", PersonCategory.GENERALS),
        HistoricalPerson("沐英", "西平侯", "洪武", "1345—1392", "明初镇守云南的重要将领，沐氏后代长期与西南防务相关。", PersonCategory.GENERALS),
        HistoricalPerson("朱能", "成国公", "建文、永乐", "1370—1406", "燕王朱棣麾下将领，参与靖难之役。", PersonCategory.GENERALS),
        HistoricalPerson("张辅", "英国公", "永乐、宣德", "1375—1449", "永乐朝主要将领之一，曾统军于交趾。", PersonCategory.GENERALS),
        HistoricalPerson("石亨", "忠国公", "景泰、天顺", "？—1460", "景泰、天顺之际的武将，参与夺门之变，后获罪。", PersonCategory.GENERALS),
        HistoricalPerson("王越", "威宁伯", "成化", "1426—1498", "成化朝边将，多次参与西北军事行动。", PersonCategory.GENERALS),
        HistoricalPerson("俞大猷", "右都督", "嘉靖、隆庆", "1503—1579", "东南抗倭名将，以军事实践和兵书见称。", PersonCategory.GENERALS, courtesyName = "志辅"),
        HistoricalPerson("谭纶", "兵部尚书", "嘉靖、隆庆", "1520—1577", "参与东南海防与北方边务整饬，常与戚继光、俞大猷并论。", PersonCategory.GENERALS, courtesyName = "子理"),
        HistoricalPerson("李成梁", "辽东总兵官", "万历", "1526—1615", "万历前期长期镇守辽东，对东北边防格局影响甚大。", PersonCategory.GENERALS),
        HistoricalPerson("麻贵", "大同总兵官", "万历", "1543—1617", "参与万历援朝及西北防务。", PersonCategory.GENERALS),
        HistoricalPerson("满桂", "辽东总兵官", "崇祯", "？—1630", "崇祯初参与京师与辽东战事。", PersonCategory.GENERALS),
        HistoricalPerson("祖大寿", "辽东总兵官", "天启、崇祯", "？—1656", "宁远、锦州一线重要将领，其生平跨越明清鼎革。", PersonCategory.GENERALS),
        HistoricalPerson("曹文诏", "总兵官", "崇祯", "？—1635", "明末镇压流寇与西北战事中的将领。", PersonCategory.GENERALS),
        HistoricalPerson("卢象升", "兵部尚书", "崇祯", "1600—1639", "明末文武兼任官员，参与北方战事。", PersonCategory.GENERALS, courtesyName = "建斗"),
        HistoricalPerson("洪承畴", "蓟辽总督", "崇祯", "1593—1665", "明末重要军事统帅，其后降清的经历使史学评价复杂。", PersonCategory.GENERALS, courtesyName = "彦演"),
        // 文人、学者与技术官僚。
        HistoricalPerson("高启", "诗人", "洪武", "1336—1374", "明初诗人，“吴中四杰”之一。", PersonCategory.LITERATI, courtesyName = "季迪"),
        HistoricalPerson("唐寅", "书画家、文学家", "弘治、正德", "1470—1524", "江南文人，以诗文、书画及其后世文化形象著称。", PersonCategory.LITERATI, courtesyName = "伯虎"),
        HistoricalPerson("文徵明", "书画家、文学家", "弘治、嘉靖", "1470—1559", "吴门文人和书画家，长期活跃于江南文化圈。", PersonCategory.LITERATI, courtesyName = "徵仲"),
        HistoricalPerson("杨慎", "文学家", "正德、嘉靖", "1488—1559", "明代文学家，大礼议后谪戍云南，著述甚丰。", PersonCategory.LITERATI, courtesyName = "用修"),
        HistoricalPerson("李贽", "思想家", "嘉靖、万历", "1527—1602", "晚明思想家，其著作与社会批评引发广泛讨论。", PersonCategory.LITERATI, courtesyName = "宏甫"),
        HistoricalPerson("袁宏道", "文学家", "万历", "1568—1610", "公安派代表人物之一，强调性灵。", PersonCategory.LITERATI, courtesyName = "中郎"),
        HistoricalPerson("董其昌", "书画家、官员", "万历、天启", "1555—1636", "晚明书画家兼官员，对后世画史影响深远。", PersonCategory.LITERATI, courtesyName = "玄宰"),
        HistoricalPerson("徐光启", "礼部尚书", "万历、天启", "1562—1633", "参与译介西学，关注农政、历法与军事技术。", PersonCategory.LITERATI, courtesyName = "子先"),
        HistoricalPerson("黄宗羲", "思想家", "崇祯", "1610—1695", "明末清初思想家，青年时期经历晚明党社活动。", PersonCategory.LITERATI, courtesyName = "太冲"),
        HistoricalPerson("陈子龙", "文学家", "崇祯", "1608—1647", "晚明诗文家，明亡前后的作品具有强烈时代印记。", PersonCategory.LITERATI, courtesyName = "卧子"),
        // 内廷人物以职掌和时代分组展示，不把“太监”作为单一政治标签。
        HistoricalPerson("汪直", "西厂提督", "成化", "？—？", "成化朝宦官，曾与西厂设置相关。", PersonCategory.COURT),
        HistoricalPerson("谷大用", "司礼监太监", "正德", "？—1527", "正德朝内廷人物，“八虎”之一。", PersonCategory.COURT),
        HistoricalPerson("张永", "司礼监太监", "正德", "？—1529", "正德朝内廷人物，参与平定宁王之乱后的政局。", PersonCategory.COURT),
        HistoricalPerson("陈矩", "司礼监太监", "万历", "1541—1611", "万历朝司礼监太监，常被作为内廷中较审慎的个案讨论。", PersonCategory.COURT),
        HistoricalPerson("王安", "司礼监秉笔太监", "泰昌、天启", "？—1621", "泰昌、天启之际的内廷人物。", PersonCategory.COURT),
        HistoricalPerson("曹化淳", "司礼监太监", "崇祯", "1589—1662", "崇祯朝内廷人物，晚明京师政局中多有记载。", PersonCategory.COURT),
        // 勋贵家系：保留子嗣本人的人物条目，并通过“父子”关系连接，避免只在父辈生平中一笔带过。
        HistoricalPerson("徐辉祖", "魏国公", "建文", "？—1407", "徐达长子，承袭魏国公；靖难后被削爵幽禁。", PersonCategory.MINISTERS),
        HistoricalPerson("徐添福", "魏国公世子", "洪武", "？—？", "徐达次子，早卒，未能承袭魏国公爵。", PersonCategory.MINISTERS),
        HistoricalPerson("徐膺绪", "中军都督佥事", "永乐", "？—？", "徐达第三子，仕至中军都督佥事。", PersonCategory.GENERALS),
        HistoricalPerson("徐增寿", "定国公", "建文、永乐", "？—1402", "徐达第四子，永乐初追封定国公。", PersonCategory.GENERALS),
        HistoricalPerson("常茂", "郑国公", "洪武", "？—1391", "常遇春长子，承袭郑国公。", PersonCategory.GENERALS),
        HistoricalPerson("常升", "开平王后裔", "洪武、建文", "？—？", "常遇春次子，明初勋贵家系成员。", PersonCategory.MINISTERS),
        HistoricalPerson("沐春", "西平侯", "洪武、建文", "？—1398", "沐英长子，承袭西平侯，镇守云南。", PersonCategory.GENERALS),
        HistoricalPerson("沐晟", "西平侯、黔国公", "永乐、洪熙、宣德", "1368—1439", "沐英次子，长期镇守云南，后进封黔国公。", PersonCategory.GENERALS),
        HistoricalPerson("沐斌", "黔国公", "正统、景泰", "？—？", "沐晟之子，承袭黔国公。", PersonCategory.GENERALS),
        HistoricalPerson("李景隆", "曹国公", "建文、永乐", "？—？", "李文忠长子，建文朝曾领兵北伐。", PersonCategory.GENERALS),
        HistoricalPerson("李增枝", "前军左都督", "建文、永乐", "？—？", "李文忠次子，官至前军左都督。", PersonCategory.GENERALS),
        HistoricalPerson("李芳英", "中都正留守", "洪武、建文", "？—？", "李文忠第三子，官至中都正留守。", PersonCategory.GENERALS),
        HistoricalPerson("刘琏", "江西参政", "洪武", "？—1380", "刘基长子，曾任监察御史、江西参政。", PersonCategory.MINISTERS, courtesyName = "孟藻"),
        HistoricalPerson("刘璟", "阁门使", "洪武、建文", "？—1402", "刘基次子，曾任阁门使、谷王长史。", PersonCategory.MINISTERS, courtesyName = "仲璟"),
    )

    private val relationData = listOf(
        PersonRelation("朱元璋", "刘基", RelationshipType.RULER_MINISTER, "洪武", "刘基参与明初建国过程与制度草创。"),
        PersonRelation("朱元璋", "徐达", RelationshipType.COMMAND, "洪武", "徐达是明初北伐与北方军事行动的重要统帅。"),
        PersonRelation("朱棣", "郑和", RelationshipType.COMMAND, "永乐", "郑和受命率领宝船队多次出使印度洋诸国。"),
        PersonRelation("杨士奇", "杨荣", RelationshipType.COLLEAGUE, "永乐、洪熙、宣德", "二人与杨溥并称“三杨”，长期参与内阁事务。"),
        PersonRelation("于谦", "朱祁钰", RelationshipType.RULER_MINISTER, "景泰", "土木之变后，于谦参与京师防务与军政处置。"),
        PersonRelation("戚继光", "俞大猷", RelationshipType.COLLEAGUE, "嘉靖、隆庆", "二人均为东南海防与军队训练的重要将领。"),
        PersonRelation("戚继光", "谭纶", RelationshipType.COLLEAGUE, "嘉靖、隆庆", "谭纶经略东南，戚继光在相关军务中任职。"),
        PersonRelation("张居正", "朱翊钧", RelationshipType.RULER_MINISTER, "万历", "万历初年，张居正以大学士主持政务。"),
        PersonRelation("张居正", "冯保", RelationshipType.COLLEAGUE, "万历", "二人同处万历初年中枢政治，具体互动应结合史料辨析。"),
        PersonRelation("魏忠贤", "朱由校", RelationshipType.RULER_MINISTER, "天启", "天启朝内廷权力结构是研究晚明政治的重要线索。"),
        PersonRelation("袁崇焕", "孙承宗", RelationshipType.COMMAND, "天启", "孙承宗经略辽东期间，袁崇焕参与宁远防务。"),
        PersonRelation("袁崇焕", "朱由检", RelationshipType.RULER_MINISTER, "崇祯", "崇祯初辽东经略与边政决策紧密关联。"),
        PersonRelation("徐达", "徐辉祖", RelationshipType.PARENT_CHILD, "洪武、建文", "徐辉祖为徐达长子，承袭魏国公。"),
        PersonRelation("徐达", "徐添福", RelationshipType.PARENT_CHILD, "洪武", "徐添福为徐达次子，早卒。"),
        PersonRelation("徐达", "徐膺绪", RelationshipType.PARENT_CHILD, "洪武、永乐", "徐膺绪为徐达第三子，任中军都督佥事。"),
        PersonRelation("徐达", "徐增寿", RelationshipType.PARENT_CHILD, "洪武、建文", "徐增寿为徐达第四子，后追封定国公。"),
        PersonRelation("常遇春", "常茂", RelationshipType.PARENT_CHILD, "洪武", "常茂为常遇春长子，承袭郑国公。"),
        PersonRelation("常遇春", "常升", RelationshipType.PARENT_CHILD, "洪武、建文", "常升为常遇春次子。"),
        PersonRelation("沐英", "沐春", RelationshipType.PARENT_CHILD, "洪武、建文", "沐春为沐英长子，承袭西平侯。"),
        PersonRelation("沐英", "沐晟", RelationshipType.PARENT_CHILD, "洪武、永乐", "沐晟为沐英次子，后进封黔国公。"),
        PersonRelation("沐晟", "沐斌", RelationshipType.PARENT_CHILD, "正统、景泰", "沐斌为沐晟之子，承袭黔国公。"),
        PersonRelation("李文忠", "李景隆", RelationshipType.PARENT_CHILD, "洪武、建文", "李景隆为李文忠长子，承袭曹国公。"),
        PersonRelation("李文忠", "李增枝", RelationshipType.PARENT_CHILD, "洪武、建文", "李增枝为李文忠次子。"),
        PersonRelation("李文忠", "李芳英", RelationshipType.PARENT_CHILD, "洪武、建文", "李芳英为李文忠第三子。"),
        PersonRelation("刘基", "刘琏", RelationshipType.PARENT_CHILD, "洪武", "刘琏为刘基长子，仕至江西参政。"),
        PersonRelation("刘基", "刘璟", RelationshipType.PARENT_CHILD, "洪武、建文", "刘璟为刘基次子，曾任阁门使。"),
    )

    private val institutionData = listOf(
        Institution(
            id = "grand-secretariat",
            name = "内阁",
            category = "中央政务",
            activeReigns = "永乐以后逐步制度化",
            function = "以内阁大学士入值文渊阁，承接票拟等中枢文书事务；其权力来自皇帝授权与实际政务运作，并非明初法定宰相的简单延续。",
            promotionPath = listOf("进士", "翰林院", "侍读／侍讲", "大学士", "首辅"),
            reforms = listOf(
                InstitutionReform("洪武十三年 · 1380", "废中书省", "丞相制度废止，六部直接对皇帝负责。"),
                InstitutionReform("永乐朝", "阁臣参预机务", "内阁在文书与决策流程中的作用逐渐加强。"),
            ),
        ),
        Institution(
            id = "six-ministries",
            name = "六部",
            category = "中央政务",
            activeReigns = "洪武至崇祯",
            function = "吏、户、礼、兵、刑、工六部掌管人事、财政、礼制、军政、司法与工程，是中央行政的核心执行机构。",
            promotionPath = listOf("生员", "举人", "进士", "主事", "员外郎", "郎中", "侍郎", "尚书"),
            reforms = listOf(
                InstitutionReform("洪武十三年 · 1380", "直达皇帝", "中书省废除后，六部改为直接向皇帝奏事。"),
            ),
        ),
        Institution(
            id = "censorate",
            name = "都察院",
            category = "监察司法",
            activeReigns = "洪武至崇祯",
            function = "负责监察百官、纠劾违法失职，设御史巡按各地；与六科给事中共同构成重要监察渠道。",
            promotionPath = listOf("进士／举人", "御史", "按察使", "副都御史", "左都御史"),
            reforms = listOf(
                InstitutionReform("洪武十五年 · 1382", "改置都察院", "御史台改为都察院，监察体系进一步定型。"),
            ),
        ),
        Institution(
            id = "jinyiwei",
            name = "锦衣卫",
            category = "皇帝亲军",
            activeReigns = "洪武十五年以后",
            function = "由皇帝亲军发展而来，兼具侍卫、仪仗、缉捕与诏狱职能。其权限、活动范围与具体案件均需按年号和史料标注。",
            promotionPath = listOf("校尉", "力士", "小旗", "总旗", "百户", "千户", "指挥佥事", "指挥使"),
            reforms = listOf(
                InstitutionReform("洪武十五年 · 1382", "设锦衣卫", "以亲军都尉府改置，形成皇帝直属侍卫机构。"),
                InstitutionReform("永乐朝", "缉捕权扩展", "与东厂等内廷机构共同构成复杂的侦缉体系。"),
            ),
        ),
        Institution(
            id = "eunuch-agencies",
            name = "司礼监与内廷诸监",
            category = "内廷宦官",
            activeReigns = "明代中后期尤具影响",
            function = "司礼监掌管内廷文书、批红等事务；内廷机构的权力大小因皇帝、时期和具体人事而变，不能简单等同于全部宦官。",
            promotionPath = listOf("内廷杂役", "小火者", "内官", "典簿", "随堂太监", "秉笔太监", "掌印太监"),
            reforms = listOf(
                InstitutionReform("永乐以后", "内廷文书职能增强", "批红等机制与外廷票拟相互衔接，实际运作因时期而异。"),
            ),
        ),
        Institution(
            id = "five-military-commissions",
            name = "五军都督府与卫所",
            category = "军事卫所",
            activeReigns = "洪武至明末",
            function = "五军都督府统辖军籍与军政系统的一部分；卫所制承担常备军与屯田等功能，后期与募兵、边镇体系并存。",
            promotionPath = listOf("军户", "旗军", "小旗", "总旗", "百户", "千户", "卫指挥使", "都督"),
            reforms = listOf(
                InstitutionReform("洪武朝", "卫所定制", "以卫所编制组织军户与地方军政。"),
                InstitutionReform("中晚明", "募兵并行", "卫所战力变化后，募兵、家丁与边镇军队的作用增加。"),
            ),
        ),
        Institution(
            id = "provincial-administration",
            name = "承宣布政使司、按察司与都指挥使司",
            category = "地方治理",
            activeReigns = "两京一十三省框架下",
            function = "地方行政、司法监察和军事分别由三司分掌；巡抚、总督等差遣在中后期逐渐成为跨区域协调的重要机制。",
            promotionPath = listOf("知县", "知府", "参政／参议", "按察使", "布政使", "巡抚", "总督"),
            reforms = listOf(
                InstitutionReform("洪武九年 · 1376", "承宣布政使司定制", "行中书省改为承宣布政使司，形成省级治理框架。"),
                InstitutionReform("中晚明", "督抚强化", "面对边防、漕运与灾荒等跨域问题，督抚差遣的重要性上升。"),
            ),
        ),
    )

    private val layerData = listOf(
        MapLayer("administration", "两京十三省", "明代行政区划与府州县层级。", true),
        MapLayer("neighbours", "周边政权", "按时间段呈现周边政权与外交关系。", true),
        MapLayer("activity", "势力范围", "仅标注有来源支撑的活动范围。", true),
        MapLayer("events", "事件地点", "按当前年份呈现可定位的史事。", false),
    )

    private val mingMapLabels = listOf(
        MapLabel("北直隶", MapLabelAnchor.NORTH),
        MapLabel("山西", MapLabelAnchor.WEST),
        MapLabel("江南", MapLabelAnchor.CENTRAL),
        MapLabel("浙江", MapLabelAnchor.EAST),
        MapLabel("朝鲜", MapLabelAnchor.KOREA),
        MapLabel("北京", MapLabelAnchor.BEIJING, isCapital = true),
        MapLabel("南京", MapLabelAnchor.NANJING, isCapital = true),
    )

    private val modernMapLabels = listOf(
        MapLabel("河北省", MapLabelAnchor.NORTH),
        MapLabel("山西省", MapLabelAnchor.WEST),
        MapLabel("江苏省", MapLabelAnchor.CENTRAL),
        MapLabel("浙江省", MapLabelAnchor.EAST),
        MapLabel("朝鲜半岛", MapLabelAnchor.KOREA),
        MapLabel("北京", MapLabelAnchor.BEIJING, isCapital = true),
        MapLabel("南京", MapLabelAnchor.NANJING, isCapital = true),
    )

    private val mapTimeline = listOf("1368", "1380", "1400", "1420", "1440", "1460", "1480", "1500")

    override fun reigns(): List<Reign> = reignData.map { reign ->
        val startYear = reign.yearRange.substringBefore("—").toInt()
        reign.copy(
            events = reign.events.map { event ->
                event.copy(year = event.year ?: seedEventYears[event.title] ?: startYear)
            },
        )
    }

    override fun people(category: PersonCategory): List<HistoricalPerson> =
        peopleData.filter { it.category == category }

    override fun allPeople(): List<HistoricalPerson> = peopleData

    override fun personRelations(): List<PersonRelation> = relationData

    override fun institutions(): List<Institution> = institutionData

    // 离线种子本身即完整资料，无需二次拉取。
    override fun personDetail(id: String): HistoricalPerson? = peopleData.firstOrNull { it.id == id }

    // 离线种子不含典章科普；天下页对空列表显示引导文案。
    override fun specialItems(): List<SpecialItem> = emptyList()

    override fun mapLayers(): List<MapLayer> = layerData

    override fun mapLabels(period: MapPeriod): List<MapLabel> =
        if (period == MapPeriod.MING) mingMapLabels else modernMapLabels

    override fun mapTimelineLabels(): List<String> = mapTimeline
}
