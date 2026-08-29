package com.ljyss.ui.relationship

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.PersonRelation
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper
import kotlin.math.cos
import kotlin.math.sin

@Composable
internal fun EventRelationshipNetwork(events: List<HistoricalEvent>) {
    val graphEvents = remember(events) { events.filter { it.participants.isNotEmpty() } }
    val defaultFocusId = remember(graphEvents) {
        graphEvents.maxByOrNull { it.participants.size }?.id.orEmpty()
    }
    var selectedFocusId by rememberSaveable { mutableStateOf(defaultFocusId) }
    val focus = graphEvents.firstOrNull { it.id == selectedFocusId } ?: graphEvents.firstOrNull()
    val participants = focus?.participants.orEmpty().take(8)
    val relatedEvents = remember(focus) {
        focus
            ?.let { event ->
                graphEvents
                    .filter { other -> other.id != event.id && other.participants.any { it in event.participants } }
                    .sortedByDescending { other -> other.participants.count { it in event.participants } }
                    .take(8)
            }
            .orEmpty()
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("事件关系图", color = Ink, fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
            Text(
                "以事件为中心：红线连出参与人物，褐线连出与其共享人物的其他事件。选择下方任一事件继续查看。",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                lineHeight = 21.sp,
            )
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(7.dp),
                contentPadding = PaddingValues(horizontal = 1.dp),
            ) {
                items(graphEvents, key = { it.id }) { event ->
                    val selected = event.id == focus?.id
                    Surface(
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { selectedFocusId = event.id },
                        shape = CutCornerShape(5.dp),
                        color = if (selected) Celadon else PaperShade,
                        border = BorderStroke(1.dp, if (selected) Celadon else LineGold),
                    ) {
                        Text(
                            text = "${event.year ?: "年份待考"}·${event.title}",
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            color = if (selected) PaperLight else Ink,
                            fontFamily = FontFamily.Serif,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
            val spokeCount = participants.size + relatedEvents.size
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(if (spokeCount > 6) 360.dp else 280.dp)
                    .clip(CutCornerShape(8.dp))
                    .background(XuanPaper),
            ) {
                val eventColor = Brass
                val personColor = Vermilion
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val center = androidx.compose.ui.geometry.Offset(size.width / 2f, size.height / 2f)
                    val spokes = participants.map { it to personColor } + relatedEvents.map { it.title to eventColor }
                    spokes.forEachIndexed { index, (_, color) ->
                        val angle = -Math.PI / 2 + (Math.PI * 2 * index / spokeCount.coerceAtLeast(1))
                        drawLine(
                            color = color.copy(alpha = .72f),
                            start = center,
                            end = androidx.compose.ui.geometry.Offset(
                                x = center.x + size.width * .39f * cos(angle).toFloat(),
                                y = center.y + size.height * .36f * sin(angle).toFloat(),
                            ),
                            strokeWidth = 2.dp.toPx(),
                            cap = StrokeCap.Round,
                        )
                    }
                }
                if (focus != null) {
                    RelationshipNode(
                        name = "${focus.year ?: ""} ${focus.title}",
                        emphasized = true,
                        modifier = Modifier.align(Alignment.Center),
                    )
                }
                val spokes = participants.map { it to personColor } + relatedEvents.map { it.title to eventColor }
                spokes.forEachIndexed { index, (label, _) ->
                    val angle = -Math.PI / 2 + (Math.PI * 2 * index / spokeCount.coerceAtLeast(1))
                    RelationshipNode(
                        name = label,
                        emphasized = false,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .offset(
                                x = maxWidth / 2 + maxWidth * .39f * cos(angle).toFloat() - 30.dp,
                                y = maxHeight / 2 + maxHeight * .36f * sin(angle).toFloat() - 16.dp,
                            ),
                    )
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Surface(modifier = Modifier.size(8.dp), shape = RoundedCornerShape(50), color = Vermilion) {}
                    Text("参与人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Surface(modifier = Modifier.size(8.dp), shape = RoundedCornerShape(50), color = Brass) {}
                    Text("关联事件", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                }
            }
            Text(
                "「${focus?.year ?: "年份待考"} ${focus?.title.orEmpty()}」参与人物 ${participants.size} 位；与其共享人物的事件 ${relatedEvents.size} 件。",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 13.sp,
            )
        }
    }
}

@Composable
internal fun RelationshipLedger(relations: List<PersonRelation>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column {
            Row(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("关系簿", color = Ink, modifier = Modifier.weight(1f), fontFamily = FontFamily.Serif, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text("按时代标注", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
            }
            relations.forEachIndexed { index, relation ->
                if (index > 0) HorizontalDivider(color = LineGold.copy(alpha = .65f))
                Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = "${relation.fromName}  ·  ${relation.type.label}  ·  ${relation.toName}",
                        color = Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text("${relation.reign}｜${relation.note}", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 21.sp)
                }
            }
        }
    }
}
