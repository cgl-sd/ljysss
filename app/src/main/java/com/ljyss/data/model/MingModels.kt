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
    val id: String = "",
    val year: Int? = null,
    /** 结束年份；单年事件与 year 相同。 */
    val endYear: Int? = null,
    /** 建制与法令／宫廷政争／战争与边防等受控分类。 */
    val eventType: String = "",
    /** 展开事件后显示；避免把史料正文硬写在 Compose 界面中。 */
    val detail: String = description,
    val participants: List<String> = emptyList(),
    /** 参与人在事件中的作用（决策者／统帅／主将等），姓名 → 作用。 */
    val participantRoles: Map<String, String> = emptyMap(),
    val consequence: String = "",
    /** 事件详情采用统一分栏；卡片仅展示摘要，独立页面展示这些正文。 */
    val sections: List<EventSection> = emptyList(),
)

data class EventSection(
    val key: String,
    val title: String,
    val content: String,
    val position: Int,
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
    /** 详情正文按栏目组织；空列表时界面自动回退为 biography 单段。 */
    val sections: List<PersonSection> = emptyList(),
    /** 面向读者的姓名；宗室女性有可考本名时与档案封号分开保存。 */
    val displayName: String = name,
    /** 仅在跨年号总档（目前为南明）中使用的首次活动年份；0 表示未设。 */
    val archiveStartYear: Int = 0,
    /** 由 event_participant 生成的正式事件反链；人物页不再从正文猜测关联事件。 */
    val relatedEvents: List<RelatedEvent> = emptyList(),
)

/** 可从人物详情直接打开的事件实体，保留稳定 id 以避免同题事件误跳。 */
data class RelatedEvent(
    val id: String,
    val year: Int,
    val title: String,
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
    /** 与该条目一一对应的专属示意图资源名。 */
    val imageAsset: String = "",
    /** 同一机构可有多条进入或升转路线；不得暗示唯一法定阶梯。 */
    val promotionTracks: List<InstitutionPromotionTrack>,
    val reforms: List<InstitutionReform>,
    val sections: List<InstitutionSection> = emptyList(),
    val people: List<InstitutionPerson> = emptyList(),
)

data class InstitutionPromotionTrack(
    val title: String,
    val steps: List<String>,
)

data class InstitutionReform(
    val year: String,
    val title: String,
    val description: String,
)

/** 机构详情的固定阅读分栏；内容与人物条目一样来自随 APK 发布的资料库。 */
data class InstitutionSection(
    val key: String,
    val title: String,
    val content: String,
    val position: Int,
)

/** 机构代表人物：只收录已在正式人物库中、并可直接跳转的实体。 */
data class InstitutionPerson(
    val id: String,
    val name: String,
    val title: String,
    val role: String,
)

/** 天下页“典章”科普条目：宫殿、器物与制度名物。 */
data class SpecialItem(
    val id: String,
    val name: String,
    val category: String,
    val era: String,
    val description: String,
    /** 与该条目一一对应的专属示意图资源名。 */
    val imageAsset: String = "",
    val sections: List<SpecialSection> = emptyList(),
    val people: List<SpecialPerson> = emptyList(),
)

/** 典章详情的通用阅读分栏：释义、形制、使用与历史脉络。 */
data class SpecialSection(
    val key: String,
    val title: String,
    val content: String,
    val position: Int,
)

/** 与典章直接相关、可跳转到正式人物库的实体。 */
data class SpecialPerson(
    val id: String,
    val name: String,
    val title: String,
    val role: String,
)

/** “我的”页穿越手册的离线条目；资料来源仅留在编辑库，阅读端不显示。 */
data class TravelGuide(
    val id: String,
    val category: String,
    val title: String,
    val subtitle: String,
    val description: String,
    val imageAsset: String,
    val sections: List<TravelGuideSection> = emptyList(),
)

data class TravelGuideSection(
    val key: String,
    val title: String,
    val content: String,
    val position: Int,
)
