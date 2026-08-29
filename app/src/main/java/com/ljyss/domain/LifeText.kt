package com.ljyss.domain

internal data class LifeBlock(val isHeader: Boolean, val isClassicalMarker: Boolean, val text: String)

internal fun parseLifeBlocks(content: String): List<LifeBlock> {
    val blocks = mutableListOf<LifeBlock>()
    for ((index, raw) in content.split("\n").withIndex()) {
        val line = raw.trim()
        when {
            line.isEmpty() -> continue
            // 栏目大标题已是“生平”，条目内同名小标题一律跳过，避免重复。
            line == "生平" -> continue
            line.startsWith("〔《明史》原文") -> blocks.add(LifeBlock(true, true, line))
            line.length <= 18 && !line.endsWith("。") && !line.endsWith("！") && !line.endsWith("？") &&
                !line.endsWith("；") && !line.contains("：") && !line.endsWith("」") ->
                blocks.add(LifeBlock(true, false, line))
            else -> blocks.add(LifeBlock(false, false, line))
        }
    }
    return blocks
}

/** 把长正文切成适合手机阅读的短段落：优先保留已有换行，再按句读边界二次分段。 */
internal fun readableParagraphs(text: String): List<String> {
    val blocks = text.replace("\r", "").trim()
        .split(Regex("\\n+"))
        .map { it.trim() }
        .filter { it.isNotEmpty() }
    if (blocks.isEmpty()) return emptyList()
    val paragraphs = mutableListOf<String>()
    for (block in blocks) {
        if (block.length <= 140) {
            paragraphs += block
            continue
        }
        val sentences = block.split(Regex("(?<=[。！？；])"))
            .map { it.trim() }
            .filter { it.isNotEmpty() }
        var buffer = ""
        for (sentence in sentences) {
            buffer += sentence
            if (buffer.length >= 130) {
                paragraphs += buffer
                buffer = ""
            }
        }
        if (buffer.isNotEmpty()) paragraphs += buffer
    }
    return paragraphs
}
