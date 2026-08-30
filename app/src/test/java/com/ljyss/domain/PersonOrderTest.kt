package com.ljyss.domain

import com.ljyss.data.SeedMingRepository
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.RelationshipType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** 人物卡排序的行为基线：分类内先官职／爵等，同级再按最早年号。 */
class PersonOrderTest {
    private fun person(reign: String, years: String, name: String = "某人") = HistoricalPerson(
        name = name,
        title = "",
        reign = reign,
        years = years,
        note = "",
        category = PersonCategory.MINISTERS,
    )

    @Test
    fun `生年缺失回落到哨兵值`() {
        // 种子库里生年不可考的人物写作「？—1449」，解析不出数字时保持末位。
        assertEquals(Int.MAX_VALUE, personBirthYear(person("正统", "？—1449")))
        assertEquals(Int.MAX_VALUE, personBirthYear(person("无考", "？—？")))
    }

    @Test
    fun `生年解析容忍首尾空白`() {
        assertEquals(1328, personBirthYear(person("洪武", "1328—1398")))
        assertEquals(1328, personBirthYear(person("洪武", " 1328 — 1398 ")))
    }

    @Test
    fun `年号次序表覆盖十七朝且首尾固定`() {
        assertEquals(17, personEraOrder.size)
        assertEquals("洪武", personEraOrder.first())
        assertEquals("崇祯", personEraOrder.last())
    }

    @Test
    fun `多朝人物按最先出现的年号定序`() {
        assertEquals(5, personChronologyRank(person("正统、天顺", "1427—1464")))
        assertEquals(2, personChronologyRank(person("永乐、洪熙、宣德", "1364—1444")))
        // 「弘光」不在十七朝表内，靠命中的「崇祯」定位。
        assertEquals(16, personChronologyRank(person("崇祯、弘光", "？—1645")))
    }

    @Test
    fun `年号表之外的人物排到末位`() {
        assertEquals(Int.MAX_VALUE, personChronologyRank(person("", "1500—1560")))
    }

    @Test
    fun `亲子关系集合只含父子与母子`() {
        assertEquals(
            setOf(RelationshipType.PARENT_CHILD, RelationshipType.MOTHER_CHILD),
            parentChildTypes(),
        )
    }

    @Test
    fun `种子库排序结果相邻有序`() {
        val sorted = sortSeedPeople()
        assertTrue(sorted.isNotEmpty())
        assertEquals(sorted, sortSeedPeople())
        assertTrue(sorted.zipWithNext().all { (left, right) -> seedComparator.compare(left, right) <= 0 })
    }

    @Test
    fun `生年不可考者之间退化为姓名字典序`() {
        val nameGroups = sortSeedPeople()
            .filter { personBirthYear(it) == Int.MAX_VALUE }
            .groupBy { personChronologyRank(it) }
            .values
            .map { group -> group.map { it.name } }
        assertTrue(nameGroups.isNotEmpty())
        assertTrue(nameGroups.all { it == it.sorted() })
    }

    @Test
    fun `帝王之间按年号次序排列`() {
        val emperors = sortSeedPeople().filter { it.category == PersonCategory.EMPERORS }
        assertEquals("朱元璋", emperors.first().name)
        assertEquals(
            emperors.map { personChronologyRank(it) },
            emperors.map { personChronologyRank(it) }.sorted(),
        )
    }

    @Test
    fun `朝臣按官职层级后再按最早年号排列`() {
        val ministers = listOf(
            person("嘉靖", "1500—1560", "嘉靖尚书").copy(title = "兵部尚书"),
            person("永乐", "1370—1430", "永乐尚书").copy(title = "礼部尚书"),
            person("洪武", "1320—1380", "侍郎").copy(title = "兵部侍郎"),
            person("洪武", "1320—1380", "首辅").copy(title = "内阁首辅"),
        )

        assertEquals(listOf("首辅", "永乐尚书", "嘉靖尚书", "侍郎"),
            orderedPeopleForCards(ministers).map { it.name })
    }

    @Test
    fun `将帅先国公后侯爵同爵按最早年号排列`() {
        val generals = listOf(
            person("永乐", "1370—1430", "永乐国公").copy(category = PersonCategory.GENERALS, title = "成国公"),
            person("洪武", "1330—1390", "洪武侯").copy(category = PersonCategory.GENERALS, title = "西平侯"),
            person("洪武", "1320—1380", "洪武公").copy(category = PersonCategory.GENERALS, title = "魏国公"),
        )

        assertEquals(listOf("洪武公", "永乐国公", "洪武侯"),
            orderedPeopleForCards(generals).map { it.name })
    }

    private val seedComparator =
        compareBy<HistoricalPerson>({ personChronologyRank(it) }, { personBirthYear(it) }, { it.name })

    private fun sortSeedPeople() = SeedMingRepository.allPeople().sortedWith(seedComparator)
}
