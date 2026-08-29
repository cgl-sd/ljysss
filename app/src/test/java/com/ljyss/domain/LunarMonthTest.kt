package com.ljyss.domain

import org.junit.Assert.assertEquals
import org.junit.Test

/** 岁月页事件排序所用的农历月序映射。 */
class LunarMonthTest {
    @Test
    fun `正月至十月按序号`() {
        val months = listOf("正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月")
        assertEquals((1..10).toList(), months.map { lunarMonthOrder(it) })
    }

    @Test
    fun `冬月与十一月同为十一`() {
        assertEquals(11, lunarMonthOrder("冬月"))
        assertEquals(11, lunarMonthOrder("十一月"))
    }

    @Test
    fun `腊月与十二月同为十二`() {
        assertEquals(12, lunarMonthOrder("腊月"))
        assertEquals(12, lunarMonthOrder("十二月"))
    }

    @Test
    fun `无法归月的写法落到末位`() {
        // 「是年」是种子数据里的实际写法，表示只系年不系月，排在腊月之后。
        assertEquals(13, lunarMonthOrder("是年"))
        assertEquals(13, lunarMonthOrder("闰正月"))
        assertEquals(13, lunarMonthOrder(""))
    }
}
