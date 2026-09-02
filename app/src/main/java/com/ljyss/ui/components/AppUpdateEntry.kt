package com.ljyss.ui.components

import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.ljyss.BuildConfig
import com.ljyss.data.UpdateSource
import com.ljyss.data.model.AppUpdate
import com.ljyss.domain.compareVersions
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.Vermilion
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private sealed interface UpdateUiState {
    object Idle : UpdateUiState
    object Checking : UpdateUiState
    data class UpToDate(val remoteTag: String) : UpdateUiState
    data class Available(val update: AppUpdate) : UpdateUiState
    data class Downloading(val downloadedBytes: Long, val totalBytes: Long) : UpdateUiState
    data class Failed(val message: String) : UpdateUiState
}

/** 侧栏里的“应用更新”入口：与页面入口同款行式样，点击行触发检查，状态展示在行下方。 */
@Composable
internal fun AppUpdateEntry(updateSource: UpdateSource, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var state by remember { mutableStateOf<UpdateUiState>(UpdateUiState.Idle) }

    fun check() {
        if (state is UpdateUiState.Checking) return
        scope.launch {
            state = UpdateUiState.Checking
            state = try {
                val update = withContext(Dispatchers.IO) { updateSource.fetchLatest() }
                if (compareVersions(update.tag, BuildConfig.VERSION_NAME) > 0) {
                    UpdateUiState.Available(update)
                } else {
                    UpdateUiState.UpToDate(update.tag)
                }
            } catch (e: Exception) {
                UpdateUiState.Failed(e.message ?: "检查更新失败")
            }
        }
    }

    fun install() {
        val update = (state as? UpdateUiState.Available)?.update ?: return
        scope.launch {
            state = UpdateUiState.Downloading(0, update.apkSizeBytes)
            val target = File(context.filesDir, "updates/update.apk")
            try {
                withContext(Dispatchers.IO) {
                    updateSource.downloadApk(update.apkUrl, target) { downloaded, total ->
                        state = UpdateUiState.Downloading(downloaded, total)
                    }
                }
                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", target)
                val intent = Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(uri, "application/vnd.android.package-archive")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
                context.startActivity(intent)
                state = UpdateUiState.Idle
            } catch (e: Exception) {
                target.delete()
                state = UpdateUiState.Failed(e.message ?: "下载或安装失败")
            }
        }
    }

    val available = state is UpdateUiState.Available
    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(CutCornerShape(6.dp))
                .clickable(onClick = ::check)
                .padding(horizontal = 12.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("◇", color = if (available) Vermilion else LineGold, fontSize = 11.sp, modifier = Modifier.width(20.dp))
            Text("应用更新", color = Ink, fontFamily = FontFamily.Serif, fontSize = 16.sp, fontWeight = FontWeight.Medium)
            Spacer(Modifier.weight(1f))
            Text("v${BuildConfig.VERSION_NAME}", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
        }
        when (val current = state) {
            UpdateUiState.Idle -> Unit
            UpdateUiState.Checking -> UpdateStateLine("正在检查更新…", InkSoft)
            is UpdateUiState.UpToDate -> UpdateStateLine("已是最新版本（${current.remoteTag}）", Brass)
            is UpdateUiState.Available -> Column(
                modifier = Modifier.padding(start = 32.dp, end = 12.dp, bottom = 8.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text("发现新版本 ${current.update.versionName}", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                if (current.update.notes.isNotBlank()) {
                    Text(current.update.notes, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp, lineHeight = 17.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
                }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    Text("立即更新", modifier = Modifier.clickable(onClick = ::install), color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(formatMegabytes(current.update.apkSizeBytes), color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                    Text("忽略", modifier = Modifier.clickable { state = UpdateUiState.Idle }, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 13.sp)
                }
            }
            is UpdateUiState.Downloading -> UpdateStateLine(
                "正在下载 ${downloadText(current.downloadedBytes, current.totalBytes)}",
                InkSoft,
            )
            is UpdateUiState.Failed -> Row(
                modifier = Modifier.padding(start = 32.dp, end = 12.dp, bottom = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(current.message, modifier = Modifier.weight(1f), color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text("重试", modifier = Modifier.clickable(onClick = ::check), color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun UpdateStateLine(text: String, color: Color) {
    Text(
        text,
        modifier = Modifier.padding(start = 32.dp, end = 12.dp, bottom = 8.dp),
        color = color,
        fontFamily = FontFamily.Serif,
        fontSize = 13.sp,
    )
}

private fun downloadText(downloadedBytes: Long, totalBytes: Long): String {
    val percent = if (totalBytes > 0) "${downloadedBytes * 100 / totalBytes}%，" else ""
    return "$percent${formatMegabytes(downloadedBytes)} / ${formatMegabytes(totalBytes)}"
}

private fun formatMegabytes(bytes: Long): String = "%.1f MB".format(bytes / 1024.0 / 1024.0)
