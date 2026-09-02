package com.ljyss.domain

/**
 * 语义化版本比较（纯规则，可 JVM 单测）。
 *
 * 解析：允许 "v" 前缀（GitHub release tag 惯例），按 "." 分段取数字字段比较，
 * 数字字段不足一侧视为 0。任一侧含无法解析的字段（如 "latest"、"1.1.1-beta"）
 * 时整体视为不可比较，返回 0（不触发更新）。
 *
 * @return a > b 返回 1；a < b 返回 -1；相等或不可比较返回 0。
 */
internal fun compareVersions(a: String, b: String): Int {
    fun numbers(raw: String): List<Long>? {
        val parts = raw.trim().removePrefix("v").split('.')
        val digits = parts.map { it.toLongOrNull() }
        return if (digits.any { it == null }) null else digits.filterNotNull()
    }
    val an = numbers(a) ?: return 0
    val bn = numbers(b) ?: return 0
    for (i in 0 until maxOf(an.size, bn.size)) {
        val av = an.getOrElse(i) { 0 }
        val bv = bn.getOrElse(i) { 0 }
        if (av != bv) return if (av > bv) 1 else -1
    }
    return 0
}
