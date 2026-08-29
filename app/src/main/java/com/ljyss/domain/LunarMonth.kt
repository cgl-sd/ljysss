package com.ljyss.domain

/** 农历月序；「是年」「闰月」等无法归月的写法一律落到 13，排在腊月之后。 */
internal fun lunarMonthOrder(month: String): Int = when (month) {
    "正月" -> 1
    "二月" -> 2
    "三月" -> 3
    "四月" -> 4
    "五月" -> 5
    "六月" -> 6
    "七月" -> 7
    "八月" -> 8
    "九月" -> 9
    "十月" -> 10
    "冬月", "十一月" -> 11
    "腊月", "十二月" -> 12
    else -> 13
}
