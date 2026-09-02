package com.ljyss.data

import com.ljyss.data.model.AppUpdate
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * GitHub Releases 更新源：读取固定仓库的最新 release，取其 [apkAssetName] 资产作为更新包。
 *
 * 发布流程（见根 README「发布」章节）：给仓库打语义化版本 tag（如 v1.2.0），
 * 把 release 构建的 ljysss.apk 上传为该 release 的资产。检查接口为 GitHub 公开
 * Releases API（未认证限流 60 次/小时，手动检查足够）；API 与下载均为 HTTPS。
 */
class GitHubUpdateSource(
    private val owner: String = "cgl-sd",
    private val repo: String = "ljysss",
    private val apkAssetName: String = "ljysss.apk",
) : UpdateSource {

    private val userAgent = "ljysss-update-check/1.0"

    override fun fetchLatest(): AppUpdate {
        val connection = URL("https://api.github.com/repos/$owner/$repo/releases/latest")
            .openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.setRequestProperty("User-Agent", userAgent)
            connection.setRequestProperty("Accept", "application/vnd.github+json")
            connection.connectTimeout = 10_000
            connection.readTimeout = 15_000
            val status = connection.responseCode
            if (status != 200) {
                throw IOException("更新服务响应异常（HTTP $status）")
            }
            val release = JSONObject(
                connection.inputStream.bufferedReader(Charsets.UTF_8).readText(),
            )
            val tag = release.optString("tag_name", "")
            val name = release.optString("name", tag)
            val notes = release.optString("body", "").trim()
            val assets = release.optJSONArray("assets")
                ?: throw IOException("发布信息缺少更新包")
            for (i in 0 until assets.length()) {
                val asset = assets.getJSONObject(i)
                if (asset.optString("name") == apkAssetName) {
                    return AppUpdate(
                        tag = tag,
                        versionName = name,
                        notes = notes,
                        apkUrl = asset.getString("browser_download_url"),
                        apkSizeBytes = asset.optLong("size", 0),
                    )
                }
            }
            throw IOException("发布信息缺少更新包 $apkAssetName")
        } finally {
            connection.disconnect()
        }
    }

    override fun downloadApk(url: String, target: File, onProgress: (Long, Long) -> Unit) {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.setRequestProperty("User-Agent", userAgent)
            connection.instanceFollowRedirects = true
            connection.connectTimeout = 10_000
            connection.readTimeout = 60_000
            val status = connection.responseCode
            if (status != 200) throw IOException("下载失败（HTTP $status）")
            val total = connection.contentLengthLong
            target.parentFile?.mkdirs()
            connection.inputStream.use { input ->
                target.outputStream().use { output ->
                    val buffer = ByteArray(8 * 1024)
                    var downloaded = 0L
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        output.write(buffer, 0, read)
                        downloaded += read
                        onProgress(downloaded, total)
                    }
                }
            }
        } catch (e: Exception) {
            target.delete()
            throw e
        } finally {
            connection.disconnect()
        }
    }
}
