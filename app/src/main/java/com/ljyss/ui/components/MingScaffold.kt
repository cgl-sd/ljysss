package com.ljyss.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

/** 四个页面共用的纸本列表容器：统一留白、行距与底部安全区。 */
@Composable
internal fun MingList(
    contentPadding: PaddingValues,
    state: LazyListState? = null,
    content: LazyListScope.() -> Unit,
) {
    val listState = state ?: rememberLazyListState()
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(XuanPaper)
            .mingScrollbar(listState),
        contentPadding = PaddingValues(
            start = 18.dp,
            top = 44.dp,
            end = 18.dp,
            bottom = contentPadding.calculateBottomPadding() + 20.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        state = listState,
        content = content,
    )
}

/** 所有纵向可滚动页面共用的右侧位置条；内容不足一屏时自动隐藏。 */
internal fun Modifier.mingScrollbar(state: LazyListState): Modifier = drawWithContent {
    drawContent()
    val layout = state.layoutInfo
    val visibleItems = layout.visibleItemsInfo
    val viewport = (layout.viewportEndOffset - layout.viewportStartOffset).toFloat()
    if (visibleItems.isEmpty() || viewport <= 0f || layout.totalItemsCount <= visibleItems.size) return@drawWithContent

    val averageItemSize = visibleItems.sumOf { it.size }.toFloat() / visibleItems.size
    val estimatedContentSize = averageItemSize * layout.totalItemsCount
    if (estimatedContentSize <= viewport) return@drawWithContent

    val trackTop = layout.viewportStartOffset.toFloat().coerceAtLeast(0f)
    val trackBottom = layout.viewportEndOffset.toFloat().coerceAtMost(size.height)
    val trackHeight = (trackBottom - trackTop).coerceAtLeast(0f)
    if (trackHeight <= 0f) return@drawWithContent

    val thumbHeight = (viewport * viewport / estimatedContentSize)
        .coerceIn(32.dp.toPx(), trackHeight)
    val maxScroll = (estimatedContentSize - viewport).coerceAtLeast(1f)
    val currentScroll = state.firstVisibleItemIndex * averageItemSize + state.firstVisibleItemScrollOffset
    val thumbTop = trackTop + (trackHeight - thumbHeight) * (currentScroll / maxScroll).coerceIn(0f, 1f)
    drawRoundRect(
        color = Vermilion.copy(alpha = 0.55f),
        topLeft = Offset(size.width - 6.dp.toPx(), thumbTop),
        size = Size(3.dp.toPx(), thumbHeight),
        cornerRadius = CornerRadius(2.dp.toPx()),
    )
}

/** 页面题字：两侧横栏夹住标题，下方一枚菱形。 */
@Composable
internal fun OrnamentalTitle(title: String) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            HorizontalDivider(modifier = Modifier.width(72.dp), color = Brass.copy(alpha = 0.7f))
            Text(
                text = "  $title  ",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 29.sp,
                fontWeight = FontWeight.Bold,
            )
            HorizontalDivider(modifier = Modifier.width(72.dp), color = Brass.copy(alpha = 0.7f))
        }
        Text("◇", color = Vermilion, fontSize = 15.sp)
    }
}
