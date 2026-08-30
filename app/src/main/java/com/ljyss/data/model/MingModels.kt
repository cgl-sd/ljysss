package com.ljyss.data.model

data class Reign(
    val title: String,
    val yearRange: String,
    val displayYear: String,
    val summary: String,
    val events: List<HistoricalEvent>,
)

data class HistoricalEvent(
    val month: String,
    val title: String,
    val description: String,
    val place: String,
    val sourceLabel: String,
    val id: String = "",
    val year: Int? = null,
    /** 展开事件后显示；避免把史料正文硬写在 Compose 界面中。 */
    val detail: String = description,
    val participants: List<String> = emptyList(),
    val consequence: String = "",
)

/** 人物六分类：帝王 / 内廷 / 宗藩 / 朝臣 / 将帅 / 文苑。爵位本身不作为分类。 */
enum class PersonCategory(val label: String, val subtitle: String) {
    EMPERORS("帝王", "皇帝与本朝君主"),
    COURT("内廷", "后妃、宫人与宦官"),
    CLAN("宗藩", "宗室、藩王与公主"),
    MINISTERS("朝臣", "辅政文臣"),
    GENERALS("将帅", "武将与督师"),
    LITERATI("文苑", "未任高官的文人与学者"),
}

data class HistoricalPerson(
    val name: String,
    val title: String,
    val reign: String,
    val years: String,
    val note: String,
    val category: PersonCategory,
    val id: String = "",
    val courtesyName: String = "",
    val biography: String = note,
    val familySummary: String = "",
    /** 史料影印像或生成的绢本示意像均用后端资源键引用。 */
    val portraitKey: String? = null,
    /** 内部数据状态；用户端不再区分来源，界面不展示此字段。 */
    val verificationStatus: String = "已校验",
    /** 服务端按栏目组织的详情正文；离线种子资料为空列表，界面自动降级为 biography 单段。 */
    val sections: List<PersonSection> = emptyList(),
    /** 面向读者的姓名；宗室女性有可考本名时与档案封号分开保存。 */
    val displayName: String = name,
    /** 仅在跨年号总档（目前为南明）中使用的首次活动年份；0 表示未设。 */
    val archiveStartYear: Int = 0,
)

/** 人物详情结构化栏目：life／family／relations／events，按服务端 position 排序。 */
data class PersonSection(
    val key: String,
    val title: String,
    val content: String,
    /** 库内给定的栏目顺序：生平 0、家族 1、人物关系 2、相关事件 3。 */
    val position: Int = 0,
)

enum class PeopleTab(val label: String) {
    PEOPLE("人物"),
    RELATIONSHIPS("关系"),
}

enum class RelationshipType(val label: String) {
    RULER_MINISTER("君臣"),
    COLLEAGUE("同僚"),
    COMMAND("统属"),
    RIVAL("政争"),
    MENTOR("师承"),
    PARENT_CHILD("父子"),
    MOTHER_CHILD("母子"),
    SPOUSE("配偶"),
    SIBLING("兄弟姐妹"),
}

data class PersonRelation(
    val fromName: String,
    val toName: String,
    val type: RelationshipType,
    val reign: String,
    val note: String,
)

data class Institution(
    val id: String,
    val name: String,
    val category: String,
    val activeReigns: String,
    val function: String,
    val promotionPath: List<String>,
    val reforms: List<InstitutionReform>,
)

data class InstitutionReform(
    val year: String,
    val title: String,
    val description: String,
)

/** 天下页“典章”科普条目：宫殿、器物与制度名物。 */
data class SpecialItem(
    val id: String,
    val name: String,
    val category: String,
    val era: String,
    val description: String,
)

enum class MapPeriod(val label: String) {
    MING("明代"),
    MODERN("现代"),
}

data class MapLayer(
    val id: String,
    val label: String,
    val description: String,
    val enabledByDefault: Boolean,
)

/** 地图文案与摆放语义属于内容数据；Compose 只负责把语义锚点渲染到当前屏幕。 */
data class MapLabel(
    val name: String,
    val anchor: MapLabelAnchor,
    val isCapital: Boolean = false,
)

enum class MapLabelAnchor {
    NORTH,
    WEST,
    CENTRAL,
    EAST,
    KOREA,
    BEIJING,
    NANJING,
}
