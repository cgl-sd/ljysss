package com.ljyss.domain

import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.RelationshipType

internal fun personBirthYear(person: HistoricalPerson): Int =
    person.years.substringBefore("—").trim().toIntOrNull() ?: Int.MAX_VALUE

internal val personEraOrder = listOf(
    "洪武", "建文", "永乐", "洪熙", "宣德", "正统", "景泰", "天顺", "成化",
    "弘治", "正德", "嘉靖", "隆庆", "万历", "泰昌", "天启", "崇祯",
)

internal fun personChronologyRank(person: HistoricalPerson): Int =
    personEraOrder.indexOfFirst { era -> person.reign.contains(era) }.let { index ->
        if (index >= 0) index else Int.MAX_VALUE
    }

/**
 * 人物卡统一排序。人物页和朝代档案都只能使用这一排序器，避免同一分类在两个入口出现
 * 不同先后。资料没有逐条保存任官月日时，以人物资料中最早出现的年号作为同级先后；
 * 生年和姓名仅用于保持结果稳定，不改变已知的官职／爵位顺序。
 */
private val rankedPersonCardComparator: Comparator<HistoricalPerson> = compareBy<HistoricalPerson>(
    { personCardRank(it) },
    { personChronologyRank(it) },
    { personBirthYear(it) },
    { it.displayName },
)

private val chronologicalPersonCardComparator: Comparator<HistoricalPerson> = compareBy<HistoricalPerson>(
    { personChronologyRank(it) },
    { personCardRank(it) },
    { personBirthYear(it) },
    { it.displayName },
)

/**
 * 未选年号时先按朝代浏览，同朝内才比较官职或爵等；选定某朝时，所有卡片已是同一朝，
 * 因而直接按官职／爵等排序。朝代档案与人物页调用同一入口。
 */
internal fun orderedPeopleForCards(
    people: List<HistoricalPerson>,
    selectedReign: String? = null,
): List<HistoricalPerson> = people.sortedWith(
    if (selectedReign == null) chronologicalPersonCardComparator else rankedPersonCardComparator,
)

private fun personCardRank(person: HistoricalPerson): Int = when (person.category) {
    PersonCategory.COURT -> when {
        person.title.contains("皇后") || person.title.contains("太后") -> 0
        person.title.contains("妃") || person.title.contains("嫔") || person.title.contains("选侍") -> 1
        else -> 2
    }
    PersonCategory.CLAN -> when {
        person.title.contains("亲王") || person.title.matches(Regex(".{1,8}王")) -> 0
        person.title.contains("郡王") -> 1
        person.title.contains("世子") -> 2
        person.title.contains("公主") -> 4
        else -> 3
    }
    PersonCategory.MINISTERS -> ministerialRank(person.title)
    PersonCategory.GENERALS -> generalRank(person.title)
    else -> 0
}

/** 明代朝臣按实际可见的最高官职层级排序，数值越小位置越靠前。 */
private fun ministerialRank(title: String): Int = when {
    title.contains("太师") || title.contains("太傅") || title.contains("太保") -> 0
    title.contains("少师") || title.contains("少傅") || title.contains("少保") -> 1
    title.contains("首辅") -> 2
    title.contains("大学士") -> 3
    title.contains("尚书") -> 4
    title.contains("都御史") -> 5
    title.contains("侍郎") -> 6
    title.contains("总督") -> 7
    title.contains("巡抚") -> 8
    title.contains("布政使") -> 9
    title.contains("按察使") -> 10
    title.contains("知府") -> 11
    title.contains("知州") -> 12
    title.contains("知县") -> 13
    title.contains("主事") -> 14
    title.contains("员外郎") || title.contains("郎中") -> 15
    title.contains("御史") -> 16
    title.contains("给事中") -> 17
    else -> 18
}

/** 将帅先以爵等排列：国公在前，侯爵次之；同级再走统一的年号先后。 */
private fun generalRank(title: String): Int = when {
    title.endsWith("公") || title.contains("国公") -> 0
    title.endsWith("侯") || title.contains("侯") -> 1
    title.endsWith("伯") || title.contains("伯") -> 2
    else -> 3
}

/** 父母与子女的亲属行都计入“子女”名单；皇帝的宗室家庭关系也由此呈现。 */
internal fun parentChildTypes() = setOf(RelationshipType.PARENT_CHILD, RelationshipType.MOTHER_CHILD)
