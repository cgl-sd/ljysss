package com.ljyss.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class UpdateVersionTest {

    @Test
    fun `相同版本返回 0`() {
        assertEquals(0, compareVersions("v1.1.1", "1.1.1"))
        assertEquals(0, compareVersions("1.10.2", "1.10.2"))
        assertEquals(0, compareVersions("v2.0.0", "v2.0.0"))
    }

    @Test
    fun `数字字段逐位比较`() {
        assertEquals(-1, compareVersions("v1.1.1", "v1.1.2"))
        assertEquals(1, compareVersions("v1.1.2", "v1.1.1"))
        assertEquals(-1, compareVersions("1.9.0", "1.10.0"))
        assertEquals(1, compareVersions("1.10.2", "1.9.9"))
        assertEquals(1, compareVersions("v2.0.0", "v1.9.9"))
    }

    @Test
    fun `缺省数字段视为 0`() {
        assertEquals(0, compareVersions("1.2", "1.2.0"))
        assertEquals(1, compareVersions("1.3", "1.2.9"))
        assertEquals(-1, compareVersions("1.2", "1.2.1"))
    }

    @Test
    fun `无法解析的版本不触发更新`() {
        assertEquals(0, compareVersions("latest", "1.1.1"))
        assertEquals(0, compareVersions("v1.1.1-beta", "1.1.1"))
        assertEquals(0, compareVersions("", "1.1.1"))
        assertEquals(0, compareVersions("abc", "1.1.1"))
    }
}
