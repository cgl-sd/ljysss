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
    fun `只有叙事性短行才判为小标题`() {
        assertTrue(parseLifeBlocks("早年经历").single().isHeader)
        assertFalse(parseLifeBlocks("早年经历。").single().isHeader)
        assertFalse(parseLifeBlocks("字号：某某").single().isHeader)
        assertFalse(parseLifeBlocks("他自号「六一」").single().isHeader)
        assertFalse(parseLifeBlocks("此事尚待考；").single().isHeader)
        assertFalse(parseLifeBlocks("影视作品").single().isHeader)
        assertFalse(parseLifeBlocks("家庭成员").single().isHeader)
        assertFalse(parseLifeBlocks("生平经历").single().isHeader)
    }

    @Test
    fun `未知短行不因字数而变成黑色标题`() {
        assertFalse(parseLifeBlocks("字".repeat(18)).single().isHeader)
        assertFalse(parseLifeBlocks("字".repeat(19)).single().isHeader)
        assertTrue(parseLifeBlocks("概览").single().isHeader)
        assertTrue(parseLifeBlocks("嘉靖年间").single().isHeader)
    }

    @Test
    fun `生平长正文按统一规则拆段而不新增栏目同名标题`() {
        val text = (1..9).joinToString("") { "第${it}句叙述人物在明代仕途中的一段经历，并包含足够长度以触发移动端分段。" }
        val blocks = parseLifeBlocks(text)
        assertEquals(text, blocks.joinToString("") { it.text })
        assertTrue(blocks.size > 1)
        assertTrue(blocks.none { it.isHeader })
        assertTrue(blocks.none { it.text == "生平经历" })
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
    fun `孤立标点合并回相邻正文而不单独成段`() {
        val paragraphs = readableParagraphs("第一句\n。\n“\n第二句\n”")
        assertTrue(paragraphs.all { it.first().isLetterOrDigit() })
        assertTrue(parseLifeBlocks("第一句\n。\n第二句").none { it.text == "。" })
    }

    @Test
    fun `生平连续短句按句读合并而不逐行展示`() {
        val text = (1..12).joinToString("\n") { "第${it}句叙事文字用于验证短行合并后的段落长度。" }
        val paragraphs = parseLifeBlocks(text).filter { !it.isHeader }.map { it.text }
        assertTrue(paragraphs.size < 12)
        assertTrue(paragraphs.dropLast(1).all { it.length >= 130 })
    }

    @Test
    fun `没有来源标题的超长生平补通用内层结构`() {
        val text = (1..45).joinToString("") { "第${it}段叙事文字足够长，用于验证移动端统一的生平分段结构。" }
        val blocks = parseLifeBlocks(text)
        assertEquals("概览", blocks.first().text)
        assertTrue(blocks.any { it.text == "纪事" })
        assertTrue(blocks.filter { !it.isHeader }.joinToString("") { it.text }.contains("第1段"))
    }

    @Test
    fun `已有叙事标题的长生平不重复补标题`() {
        val text = "早年\n" + (1..45).joinToString("") { "第${it}段叙事文字足够长，用于验证移动端统一的生平分段结构。" }
        val blocks = parseLifeBlocks(text)
        assertEquals(1, blocks.count { it.text == "早年" })
        assertFalse(blocks.any { it.text == "概览" || it.text == "纪事" })
    }

    @Test
    fun `生平折叠阈值固定为一千二百字`() {
        assertEquals(1200, LifeCollapseCharacterLimit)
    }

    @Test
    fun `空白输入返回空表`() {
        assertEquals(emptyList<String>(), readableParagraphs("   \n  "))
    }
}
