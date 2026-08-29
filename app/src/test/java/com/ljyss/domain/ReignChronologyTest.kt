package com.ljyss.domain

import com.ljyss.data.SeedMingRepository
import com.ljyss.data.model.Reign
import org.junit.Assert.assertEquals
import org.junit.Test

/** 年号起讫与「元年／十年」汉字纪年的现有行为基线。 */
class ReignChronologyTest {
    private fun reign(yearRange: String, title: String = "洪武") =
        Reign(title = title, yearRange = yearRange, displayYear = "", summary = "", events = emptyList())

    @Test
    fun `起讫年从区间解析`() {
        val subject = reign("1368—1398")
        assertEquals(1368, subject.startYear())
        assertEquals(1398, subject.endYear())
    }

    @Test
    fun `单值年号起讫同年`() {
        // 洪熙只有一年，种子数据里 yearRange 就是不带破折号的 "1425"。
        val subject = reign("1425", title = "洪熙")
        assertEquals(1425, subject.startYear())
        assertEquals(1425, subject.endYear())
    }

    @Test
    fun `年纪标注写出元年与十年`() {
        val hongwu = reign("1368—1398")
        assertEquals("洪武元年 · 1368", hongwu.yearLabel(1368))
        assertEquals("洪武十年 · 1377", hongwu.yearLabel(1377))
        assertEquals("洪武十一年 · 1378", hongwu.yearLabel(1378))
        assertEquals("洪武二十年 · 1387", hongwu.yearLabel(1387))
        assertEquals("洪武二十一年 · 1388", hongwu.yearLabel(1388))
    }

    @Test
    fun `年纪标注与种子库展示串逐朝一致`() {
        val mismatches = SeedMingRepository.reigns()
            .filter { it.yearLabel(it.startYear()) != it.displayYear }
            .map { "${it.title}: 计算值「${it.yearLabel(it.startYear())}」≠ 种子「${it.displayYear}」" }
        assertEquals(emptyList<String>(), mismatches)
    }
}
