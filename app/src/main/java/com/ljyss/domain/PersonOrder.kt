package com.ljyss.domain

import com.ljyss.data.model.HistoricalPerson
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

/** 父母与子女的亲属行都计入“子女”名单；皇帝的宗室家庭关系也由此呈现。 */
internal fun parentChildTypes() = setOf(RelationshipType.PARENT_CHILD, RelationshipType.MOTHER_CHILD)
