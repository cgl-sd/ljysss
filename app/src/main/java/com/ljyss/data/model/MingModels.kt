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

enum class PersonCategory(val label: String) {
    EMPERORS("皇帝"),
    MINISTERS("名臣"),
    GENERALS("名将"),
    LITERATI("文人"),
    EUNUCHS("宦官"),
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
    /** 史料影印像或生成的绢本示意像均用后端资源键引用。 */
    val portraitKey: String? = null,
    val sourceLabel: String = "《明史》人物列传（待卷次校核）",
)

enum class PeopleTab(val label: String) {
    PEOPLE("人物"),
    RELATIONSHIPS("关系"),
    INSTITUTIONS("机构"),
}

enum class RelationshipType(val label: String) {
    RULER_MINISTER("君臣"),
    COLLEAGUE("同僚"),
    COMMAND("统属"),
    RIVAL("政争"),
    MENTOR("师承"),
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
