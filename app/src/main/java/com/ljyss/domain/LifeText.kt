package com.ljyss.domain

internal data class LifeBlock(val isHeader: Boolean, val isClassicalMarker: Boolean, val text: String)

private val NarrativeInnerHeadings = setOf(
    "概览", "纪事", "早年", "早年经历", "早年生涯", "早期经历", "早期生涯", "晚年", "晚年经历", "晚年生涯", "求学",
    "仕途", "仕宦", "从政", "入仕", "经历", "事迹", "生涯", "官宦", "军旅", "征战",
    "战事", "戍边", "任职", "政绩", "为政举措", "即位", "登基", "驾崩", "去世", "逝世",
    "殉国", "遗诏", "后事", "身世", "大礼议", "靖难之役", "国本之争", "夺门之变", "土木堡之变",
)
private val ReignInnerHeading = Regex(
    "^(至正|洪武|建文|永乐|洪熙|宣德|正统|景泰|天顺|成化|弘治|正德|嘉靖|隆庆|万历|泰昌|天启|崇祯|弘光|隆武|绍武|永历).*(年间|朝)$",
)
private val EventInnerHeading = Regex("^.{2,16}(之役|之变)$")

/** 生平中只有经过语义审校的经历/年代标题使用深色标题样式，避免作品、子嗣等短行误显眼。 */
internal fun isNarrativeInnerHeading(line: String): Boolean =
    line in NarrativeInnerHeadings || ReignInnerHeading.matches(line) || EventInnerHeading.matches(line)

internal fun parseLifeBlocks(content: String): List<LifeBlock> {
    val blocks = mutableListOf<LifeBlock>()
    for (raw in content.split("\n")) {
        val line = raw.trim()
        when {
            line.isEmpty() -> continue
            // 栏目大标题已是“生平”，条目内同名小标题一律跳过，避免重复。
            line == "生平" -> continue
            line.startsWith("〔《明史》原文") -> blocks.add(LifeBlock(true, true, line))
            isNarrativeInnerHeading(line) ->
                blocks.add(LifeBlock(true, false, line))
            // 同一规则适用于所有人物：正文按句读拆成便于手机阅读的短段；不额外
            // 制造与外层“生平”相近的标题。
            else -> readableParagraphs(line).forEach { paragraph ->
                blocks.add(LifeBlock(false, false, paragraph))
            }
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
