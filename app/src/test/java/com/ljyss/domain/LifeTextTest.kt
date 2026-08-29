package com.ljyss.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** 生平栏目分块与移动端分段规则的现有行为基线。 */
class LifeTextTest {
    @Test
    fun `空行与同名小标题被丢弃`() {
        val blocks = parseLifeBlocks("生平\n\n\n第一段。\n")
        assertEquals(listOf("第一段。"), blocks.map { it.text })
        assertFalse(blocks.single().isHeader)
    }

    @Test
    fun `明史原文块同时标为标题与古典块`() {
        val block = parseLifeBlocks("〔《明史》原文〕卷九〇·食货志").single()
        assertTrue(block.isHeader)
        assertTrue(block.isClassicalMarker)
    }

    @Test
    fun `短行带句读或冒号时不判为小标题`() {
        assertTrue(parseLifeBlocks("早年经历").single().isHeader)
        assertFalse(parseLifeBlocks("早年经历。").single().isHeader)
        assertFalse(parseLifeBlocks("字号：某某").single().isHeader)
        assertFalse(parseLifeBlocks("他自号「六一」").single().isHeader)
        assertFalse(parseLifeBlocks("此事尚待考；").single().isHeader)
    }

    @Test
    fun `十八字是无句读短行判为标题的边界`() {
        assertTrue(parseLifeBlocks("字".repeat(18)).single().isHeader)
        assertFalse(parseLifeBlocks("字".repeat(19)).single().isHeader)
    }

    @Test
    fun `短块原样保留为一行一段`() {
        assertEquals(listOf("第一行", "第二行"), readableParagraphs("第一行\n第二行"))
    }

    @Test
    fun `长块按句读聚合且拼接无损`() {
        val text = (1..8).joinToString("") { "第${it}句讲述一段足够长的内容以便触发聚合规则的阈值测试。" }
        val paragraphs = readableParagraphs(text)
        assertEquals(text, paragraphs.joinToString(""))
        assertTrue(paragraphs.size > 1)
        assertTrue(paragraphs.dropLast(1).all { it.length >= 130 })
    }

    @Test
    fun `回车与首尾空白被清理`() {
        val paragraphs = readableParagraphs("  第一行\r\n第二行  ")
        assertEquals(listOf("第一行", "第二行"), paragraphs)
    }

    @Test
    fun `空白输入返回空表`() {
        assertEquals(emptyList<String>(), readableParagraphs("   \n  "))
    }
}
