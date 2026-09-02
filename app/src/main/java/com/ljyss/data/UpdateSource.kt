package com.ljyss.data

import com.ljyss.data.model.AppUpdate
import java.io.File

/**
 * 应用更新源。实现负责网络访问，调用方负责在后台线程执行。
 */
interface UpdateSource {

    /** 获取最新发布；无网络、HTTP 异常或无 APK 资产时抛 [Exception]。 */
    fun fetchLatest(): AppUpdate

    /**
     * 下载 APK 到 [target]（覆盖已存在文件）；失败时删除残留文件并抛出。
     * [onProgress] 以 (已下载字节, 总字节) 回调；总字节未知时为 0。
     */
    fun downloadApk(url: String, target: File, onProgress: (Long, Long) -> Unit)
}
