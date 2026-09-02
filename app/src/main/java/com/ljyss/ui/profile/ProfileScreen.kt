package com.ljyss.ui.profile

import android.annotation.SuppressLint
import android.content.Intent
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.MenuBook
import androidx.compose.material.icons.outlined.SystemUpdate
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.ljyss.BuildConfig
import com.ljyss.data.MingRepository
import com.ljyss.data.UpdateSource
import com.ljyss.data.model.TravelGuide
import com.ljyss.data.model.AppUpdate
import com.ljyss.domain.compareVersions
import com.ljyss.ui.components.MingArticleSection
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.components.Seal
import com.ljyss.ui.search.SearchDestination
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private val GuideCardImageWidth = 112.dp
private val GuideCardImageHeight = 94.dp
private val GuideDetailImageHeight = 220.dp

/** “我的”页的知识目录。内容来自随 APK 发布的 SQLite，不依赖网络。 */
@Composable
internal fun ProfileScreen(
    repository: MingRepository,
    updateSource: UpdateSource,
    contentPadding: PaddingValues,
    searchDestination: SearchDestination? = null,
    onSearchDestinationConsumed: () -> Unit = {},
    onSearch: () -> Unit = {},
) {
    val guides = remember(repository) { repository.travelGuides() }
    var selectedGuideId by rememberSaveable { mutableStateOf<String?>(null) }
    val listState = rememberLazyListState()
    LaunchedEffect(searchDestination) {
        val guideId = searchDestination?.guideId ?: return@LaunchedEffect
        if (guides.any { it.id == guideId }) selectedGuideId = guideId
        onSearchDestinationConsumed()
    }
    val selectedGuide = guides.firstOrNull { it.id == selectedGuideId }
    BackHandler(enabled = selectedGuide != null) { selectedGuideId = null }
    if (selectedGuide != null) {
        GuideDetailScreen(selectedGuide, contentPadding)
        return
    }

    MingList(contentPadding, state = listState) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                MingMasthead(onSearch)
                OrnamentalTitle("我的")
            }
        }
        item {
            UpdateSection(
                updateSource = updateSource,
                modifier = Modifier.padding(bottom = 10.dp),
            )
        }
        item { TravelGuideSectionTitle() }
        items(guides, key = { it.id }) { guide ->
            TravelGuideCard(guide, onOpen = { selectedGuideId = guide.id })
        }
    }
}

@Composable
private fun TravelGuideSectionTitle() {
    Surface(
        shape = CutCornerShape(5.dp),
        color = PaperShade.copy(alpha = 0.48f),
        border = BorderStroke(1.dp, LineGold),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 11.dp, vertical = 7.dp),
            horizontalArrangement = Arrangement.spacedBy(7.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.MenuBook, contentDescription = null, tint = Vermilion, modifier = Modifier.height(19.dp))
            Text("穿越手册", color = Ink, fontFamily = FontFamily.Serif, fontSize = 17.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun TravelGuideCard(guide: TravelGuide, onOpen: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().heightIn(min = 118.dp).clickable(onClick = onOpen),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = .96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            GuideAssetImage(
                asset = guide.imageAsset,
                contentDescription = "${guide.title}插绘",
                modifier = Modifier.width(GuideCardImageWidth).height(GuideCardImageHeight).clip(CutCornerShape(5.dp)),
                contentScale = ContentScale.Crop,
            )
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(guide.title, color = Ink, modifier = Modifier.weight(1f), fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Seal(guide.category)
                }
                Text(guide.description, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 19.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(guide.subtitle, color = Brass, fontFamily = FontFamily.Serif, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

@Composable
private fun GuideDetailScreen(guide: TravelGuide, contentPadding: PaddingValues) {
    MingList(contentPadding) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = CutCornerShape(10.dp),
                border = BorderStroke(1.3.dp, LineGold),
                colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = .96f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(guide.title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                    Text(guide.category + "｜" + guide.subtitle, color = Brass, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    GuideAssetImage(
                        asset = guide.imageAsset,
                        contentDescription = "${guide.title}专题插绘",
                        modifier = Modifier.fillMaxWidth().height(GuideDetailImageHeight).clip(CutCornerShape(7.dp)),
                        contentScale = ContentScale.Crop,
                    )
                    val sections = guide.sections.sortedBy { it.position }.filter { it.content.isNotBlank() }
                    if (sections.isEmpty()) MingArticleSection("概览", guide.description)
                    else sections.forEach { section -> MingArticleSection(section.title, section.content) }
                }
            }
        }
    }
}

@Composable
@SuppressLint("DiscouragedApi", "LocalContextResourcesRead")
private fun GuideAssetImage(asset: String, contentDescription: String, modifier: Modifier, contentScale: ContentScale) {
    val context = LocalContext.current
    val resource = remember(asset, context.packageName) {
        context.resources.getIdentifier(asset, "drawable", context.packageName).takeIf { it != 0 }
    }
    Box(modifier = modifier.background(PaperShade.copy(alpha = .52f)), contentAlignment = Alignment.Center) {
        if (resource != null) {
            Image(painterResource(resource), contentDescription, modifier = Modifier.fillMaxSize(), contentScale = contentScale)
        } else {
            Icon(Icons.Outlined.MenuBook, contentDescription = null, tint = Brass, modifier = Modifier.height(34.dp))
        }
    }
}
private sealed interface UpdateUiState {
    object Idle : UpdateUiState
    object Checking : UpdateUiState
    data class UpToDate(val remoteTag: String) : UpdateUiState
    data class Available(val update: AppUpdate) : UpdateUiState
    data class Downloading(val downloadedBytes: Long, val totalBytes: Long) : UpdateUiState
    data class Failed(val message: String) : UpdateUiState
}

/** “应用更新”卡片：手动检查 GitHub 最新发布，发现新版本时下载并引导安装。 */
@Composable
private fun UpdateSection(updateSource: UpdateSource, modifier: Modifier = Modifier) {
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

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        color = PaperLight.copy(alpha = 0.96f),
        border = BorderStroke(1.25.dp, LineGold),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.SystemUpdate, contentDescription = null, tint = Vermilion, modifier = Modifier.height(19.dp))
                Text("应用更新", modifier = Modifier.padding(start = 7.dp).weight(1f), color = Ink, fontFamily = FontFamily.Serif, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                Text("当前 v${BuildConfig.VERSION_NAME}", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
            }
            when (val current = state) {
                UpdateUiState.Idle -> UpdateStateRow(
                    text = "从 GitHub 最新发布检查并安装新版本",
                    buttonLabel = "检查更新",
                    onButton = ::check,
                )
                UpdateUiState.Checking -> Text("正在检查更新…", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 13.sp)
                is UpdateUiState.UpToDate -> Text("已是最新版本（${current.remoteTag}）", color = Brass, fontFamily = FontFamily.Serif, fontSize = 13.sp)
                is UpdateUiState.Available -> Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text("发现新版本 ${current.update.versionName}", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    if (current.update.notes.isNotBlank()) {
                        Text(current.update.notes, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp, lineHeight = 17.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        UpdateActionButton("立即更新", onClick = ::install)
                        Text(formatMegabytes(current.update.apkSizeBytes), color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                        Text("忽略", modifier = Modifier.clickable { state = UpdateUiState.Idle }, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 13.sp)
                    }
                }
                is UpdateUiState.Downloading -> Text(
                    "正在下载 ${downloadText(current.downloadedBytes, current.totalBytes)}",
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 13.sp,
                )
                is UpdateUiState.Failed -> UpdateStateRow(
                    text = current.message,
                    buttonLabel = "重试",
                    onButton = ::check,
                )
            }
        }
    }
}

@Composable
private fun UpdateStateRow(text: String, buttonLabel: String, onButton: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(text, modifier = Modifier.weight(1f), color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 13.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
        UpdateActionButton(buttonLabel, onClick = onButton)
    }
}

@Composable
private fun UpdateActionButton(label: String, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.clip(CutCornerShape(5.dp)).clickable(onClick = onClick),
        shape = CutCornerShape(5.dp),
        color = Vermilion,
    ) {
        Text(label, modifier = Modifier.padding(horizontal = 13.dp, vertical = 5.dp), color = PaperLight, fontFamily = FontFamily.Serif, fontSize = 13.sp, fontWeight = FontWeight.Bold)
    }
}

private fun downloadText(downloadedBytes: Long, totalBytes: Long): String {
    val percent = if (totalBytes > 0) "${downloadedBytes * 100 / totalBytes}%，" else ""
    return "$percent${formatMegabytes(downloadedBytes)} / ${formatMegabytes(totalBytes)}"
}

private fun formatMegabytes(bytes: Long): String = "%.1f MB".format(bytes / 1024.0 / 1024.0)
