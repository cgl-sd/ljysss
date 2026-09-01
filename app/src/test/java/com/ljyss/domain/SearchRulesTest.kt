package com.ljyss.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** 搜索匹配规则：归一化、双路匹配与排序的行为基线。 */
class SearchRulesTest {
    @Test
    fun `归一化去除首尾空白并折叠连续空白`() {
        assertEquals("于谦 兵部尚书", normalizeSearchText("  于谦\t兵部尚书  "))
    }

    @Test
    fun `归一化拉丁字母转小写`() {
        assertEquals("yongle", normalizeSearchText("YongLe"))
    }

    @Test
    fun `归一化全角字母数字转半角`() {
        assertEquals("abc 123", normalizeSearchText("ＡＢＣ １２３"))
    }

    @Test
    fun `归一化全角空格转半角空格`() {
        assertEquals("郑 成功", normalizeSearchText("郑　成功"))
    }

    @Test
    fun `归一化对中文与年号文本原样保留`() {
        assertEquals("土木堡之变", normalizeSearchText("土木堡之变"))
    }

    @Test
    fun `汉字转拼音无音调无分隔`() {
        assertEquals("yuqian", toPinyin("于谦"))
        assertEquals("zhudi", toPinyin("朱棣"))
        assertEquals("tumubao", toPinyin("土木堡"))
    }

    @Test
    fun `非汉字原样保留`() {
        assertEquals("1449 tumubao", toPinyin("1449 土木堡"))
    }

    @Test
    fun `拼音查询命中汉字文本`() {
        assertEquals(MatchHit(0, true), bestMatch("于谦 于谦 兵部尚书", "yuqian"))
        assertEquals(MatchHit(2, false), bestMatch("于谦 兵部尚书", "qian"))
        assertNull(bestMatch("徐达 明朝开国功臣", "zhudi"))
    }

    @Test
    fun `中文查询命中汉字文本`() {
        assertEquals(MatchHit(0, true), bestMatch("于谦 于谦 兵部尚书", "于谦"))
    }

    @Test
    fun `双路取更早位置`() {
        // 中文查询：汉字文本位置 3 命中早于拼音文本位置 7 → 取 3
        assertEquals(MatchHit(3, true), bestMatch("于谦 徐达", "徐达"))
        // 拼音查询：汉字文本未命中，拼音文本 0 位命中 → 取 0
        assertEquals(MatchHit(0, true), bestMatch("于谦 徐达", "yuqian"))
    }

    @Test
    fun `拼音查询带空格也能命中`() {
        assertEquals(MatchHit(0, true), bestMatch("于谦 兵部尚书", "yu qian"))
    }

    @Test
    fun `整词命中区分于前缀命中`() {
        // 朱棣拼音"zhudi"在"zhudianyang"内是前缀命中（非整词）
        assertEquals(MatchHit(0, false), bestMatch("zhudianyang", "zhudi"))
        assertEquals(MatchHit(0, true), bestMatch("zhudi zhudi", "zhudi"))
        // 中文里"于谦山"非整词
        assertEquals(MatchHit(0, false), bestMatch("于谦山 徐达", "于谦"))
    }

    @Test
    fun `排序按位置升序再整词优先并剔除未命中`() {
        val ranked = rankByFirstMatch(
            listOf(
                "late" to MatchHit(8, true),
                "miss" to null,
                "prefix" to MatchHit(0, false),
                "first" to MatchHit(0, true),
                "mid" to MatchHit(3, true),
            ),
        )
        assertEquals(listOf("first", "prefix", "mid", "late"), ranked)
    }

    @Test
    fun `同位置同整词性保持目录构建顺序`() {
        val ranked = rankByFirstMatch(
            listOf(
                "人物" to MatchHit(0, true),
                "年号" to MatchHit(0, true),
                "大事" to MatchHit(0, true),
            ),
        )
        assertEquals(listOf("人物", "年号", "大事"), ranked)
    }
}
