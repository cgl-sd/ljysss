package com.ljyss.ui.relationship

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.PersonRelation
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

/** 关系页两个分组的小标题：事件在上、人物之间的关系在下。 */
@Composable
internal fun SectionTitle(title: String) {
    Column(modifier = Modifier.padding(top = 18.dp, bottom = 8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            HorizontalDivider(modifier = Modifier.width(28.dp), color = Vermilion)
            Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        }
        HorizontalDivider(modifier = Modifier.padding(top = 6.dp), color = LineGold.copy(alpha = .65f))
    }
}

/** 事件卡片：标题＋年份、摘要、受控分类。点击进入事件详情页。 */
@Composable
internal fun EventHubCard(event: HistoricalEvent, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = event.title,
                    modifier = Modifier.weight(1f),
                    color = Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(yearLabel(event), color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
            }
            Text(
                text = event.description,
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 13.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            event.eventType.takeIf { it.isNotBlank() && it != "未分类" }?.let { type ->
                Text(type, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
            }
        }
    }
}

/** 关系卡片：「甲 · 类型 · 乙」＋时代与备注。点击进入关系详情页。 */
@Composable
internal fun RelationHubCard(relation: PersonRelation, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = "${relation.fromName} · ${relation.type.label} · ${relation.toName}",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "${relation.reign}｜${relation.note}",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 13.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

private fun yearLabel(event: HistoricalEvent): String = event.year?.let { start ->
    val end = event.endYear
    if (end != null && end != start) "$start—$end" else start.toString()
}.orEmpty()
