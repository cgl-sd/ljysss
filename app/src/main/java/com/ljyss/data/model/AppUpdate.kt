package com.ljyss.data.model

/** 更新源返回的最新发布信息。 */
data class AppUpdate(
    val tag: String,
    val versionName: String,
    val notes: String,
    val apkUrl: String,
    val apkSizeBytes: Long,
)
