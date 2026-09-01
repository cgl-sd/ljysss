package com.ljyss.domain

import java.text.Normalizer

/**
 * 搜索匹配规则（纯规则，可 JVM 单测）。
 *
 * 归一化——查询与索引文本使用同一套规则：
 * 1. Unicode NFC 正规化（组合字符归一）；
 * 2. 拉丁字母转小写；
 * 3. 全角字母、数字转半角（Ａ→A，１→1）；
 * 4. 全角空格转半角，连续空白折叠为单个空格，首尾去除。
 *
 * 匹配——中文与拼音双路：
 * - 中文查询直接命中归一化后的汉字文本；
 * - 拼音查询（含中文查询转成的拼音）命中归一化后的拼音文本；
 * 两条路线各自取首次出现位置，取更早者；都未命中即排除。
 *
 * 排序——三级键：
 * 1. 首次出现位置升序（最先开始、最先出现的条目排最前）；
 * 2. 同一位置：整词精确命中（前后为字界）优先于前缀/子串命中；
 * 3. 仍相同：保持目录构建顺序（稳定排序）。
 */
internal fun normalizeSearchText(raw: String): String {
    val nfc = Normalizer.normalize(raw, Normalizer.Form.NFC)
    val sb = StringBuilder(nfc.length)
    for (ch in nfc) {
        val c = when {
            ch in '\uFF21'..'\uFF3A' || ch in '\uFF41'..'\uFF5A' || ch in '\uFF10'..'\uFF19' ->
                (ch.code - 0xFEE0).toChar()
            ch == '\u3000' -> ' '
            else -> ch
        }
        sb.append(c)
    }
    return sb.toString().lowercase().replace(Regex("\\s+"), " ").trim()
}

/** 一次命中：index 为首次出现位置；exact 表示命中段前后为字界（整词命中）。 */
internal data class MatchHit(val index: Int, val exact: Boolean)

/** 在归一化文本中找归一化查询的首次命中；未命中返回 null。 */
internal fun firstMatch(normalizedHaystack: String, normalizedQuery: String): MatchHit? {
    if (normalizedQuery.isEmpty()) return MatchHit(0, true)
    val idx = normalizedHaystack.indexOf(normalizedQuery)
    if (idx < 0) return null
    val boundary: (Char?) -> Boolean = { c -> c == null || !c.isLetterOrDigit() }
    val exact = boundary(normalizedHaystack.getOrNull(idx - 1)) &&
        boundary(normalizedHaystack.getOrNull(idx + normalizedQuery.length))
    return MatchHit(idx, exact)
}

/**
 * 把文本转成拼音（小写、无音调、汉字间无分隔），用于拼音检索。
 * 未收录汉字原样保留（数字、字母、标点不动）。
 */
internal fun toPinyin(raw: String): String {
    val sb = StringBuilder(raw.length * 2)
    for (ch in raw) {
        sb.append(PinyinTable.pinyinOf(ch) ?: ch)
    }
    return sb.toString()
}

/**
 * 双路匹配取更优命中：中文查询命中汉字文本、拼音查询（含中文查询转拼音）命中拼音文本，
 * 两条路线分别取首次命中，取位置更早者；位置相同取整词命中者；都未命中返回 null。
 */
internal fun bestMatch(normalizedHaystack: String, normalizedQuery: String): MatchHit? {
    if (normalizedQuery.isEmpty()) return MatchHit(0, true)
    val hanHit = firstMatch(normalizedHaystack, normalizedQuery)
    val pyQuery = toPinyin(normalizedQuery).replace(" ", "")
    val pyHit = if (pyQuery.isEmpty()) null else firstMatch(toPinyin(normalizedHaystack), pyQuery)
    return listOfNotNull(hanHit, pyHit)
        .minWithOrNull(compareBy<MatchHit> { it.index }.thenBy { !it.exact })
}

/**
 * 排序：首次出现位置升序 → 同一位置整词命中优先 → 保持传入顺序（目录构建顺序）。
 * 未命中的候选剔除。
 */
internal fun <T> rankByFirstMatch(candidates: List<Pair<T, MatchHit?>>): List<T> =
    candidates
        .filter { it.second != null }
        .sortedWith(
            compareBy<Pair<T, MatchHit?>> { it.second!!.index }
                .thenBy { !it.second!!.exact },
        )
        .map { it.first }
