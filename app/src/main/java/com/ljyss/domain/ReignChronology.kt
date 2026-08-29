package com.ljyss.domain

import com.ljyss.data.model.Reign

internal fun Reign.startYear(): Int = yearRange.substringBefore("—").toInt()

internal fun Reign.endYear(): Int = yearRange.substringAfter("—", yearRange).toInt()

internal fun Reign.yearLabel(year: Int): String =
    "$title${chineseYearNumber(year - startYear() + 1)}年 · $year"

private fun chineseYearNumber(value: Int): String {
    val digits = listOf("零", "一", "二", "三", "四", "五", "六", "七", "八", "九")
    return when {
        value < 10 -> if (value == 1) "元" else digits[value]
        value < 20 -> if (value == 10) "十" else "十${digits[value % 10]}"
        value % 10 == 0 -> "${digits[value / 10]}十"
        else -> "${digits[value / 10]}十${digits[value % 10]}"
    }
}
