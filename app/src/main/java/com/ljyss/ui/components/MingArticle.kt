package com.ljyss.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.RelatedEvent
import com.ljyss.domain.readableParagraphs
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.Vermilion

/** 人物、事件、天下详情共用的阅读分栏，保持同一标题、分隔线与自然段节奏。 */
@Composable
internal fun MingArticleSection(title: String, content: String) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            readableParagraphs(content).forEach { paragraph ->
                Text(
                    paragraph,
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 26.sp,
                    textAlign = TextAlign.Justify,
                )
            }
        }
    }
}

/** 相关人物只显示姓名；可点、自动换行，不再挤在一条横向滚动行里。 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun MingPersonLinks(
    names: List<String>,
    onOpenPerson: (String) -> Unit,
    modifier: Modifier = Modifier,
    roles: Map<String, String> = emptyMap(),
) {
    val distinctNames = names.filter { it.isNotBlank() }.distinct()
    FlowRow(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
        verticalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        distinctNames.forEach { name ->
            Surface(
                onClick = { onOpenPerson(name) },
                shape = CutCornerShape(4.dp),
                color = Vermilion.copy(alpha = 0.08f),
                border = BorderStroke(1.dp, Vermilion.copy(alpha = 0.65f)),
            ) {
                Column(modifier = Modifier.padding(horizontal = 9.dp, vertical = 6.dp)) {
                    Text(
                        name,
                        color = Vermilion,
                        fontFamily = FontFamily.Serif,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    roles[name]?.takeIf { it.isNotBlank() }?.let { role ->
                        Text(
                            role,
                            color = Vermilion.copy(alpha = 0.75f),
                            fontFamily = FontFamily.Serif,
                            fontSize = 11.sp,
                        )
                    }
                }
            }
        }
    }
}

/** 人物详情的事件反链和人物标签采用同一多行标签节奏。 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun MingEventLinks(
    events: List<RelatedEvent>,
    onOpenEvent: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    FlowRow(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
        verticalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        events.distinctBy { it.id.ifBlank { "${it.year}:${it.title}" } }.forEach { event ->
            val key = event.id.ifBlank { "${event.year}:${event.title}" }
            // 点击器放在文字承载层：标签的可见区域就是点击区域，避免人物长页中的
            // 外层容器在部分设备上吞掉事件卡的指针命中。
            Card(
                modifier = Modifier.widthIn(max = 178.dp),
                shape = CutCornerShape(4.dp),
                colors = CardDefaults.cardColors(containerColor = Vermilion.copy(alpha = 0.08f)),
                border = BorderStroke(1.dp, Vermilion.copy(alpha = 0.65f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
            ) {
                Text(
                    text = "${event.year}年 · ${event.title}",
                    modifier = Modifier
                        .clickable { onOpenEvent(key) }
                        .padding(horizontal = 9.dp, vertical = 6.dp),
                    color = Vermilion,
                    fontFamily = FontFamily.Serif,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}
