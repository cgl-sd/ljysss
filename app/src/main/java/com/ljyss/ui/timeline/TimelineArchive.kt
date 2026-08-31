package com.ljyss.ui.timeline

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.R
import com.ljyss.data.model.Reign
import com.ljyss.domain.lunarMonthOrder
import com.ljyss.domain.startYear
import com.ljyss.domain.yearLabel
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Indigo
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

@Composable
internal fun TimelineArchive(
    reign: Reign,
    selectedYear: Int,
    expandedEventId: String?,
    onEventClick: (String) -> Unit,
    onOpenPerson: (String) -> Unit,
) {
    val orderedEvents = reign.events.sortedWith(
        compareBy<HistoricalEvent>({ it.year ?: Int.MAX_VALUE }, { lunarMonthOrder(it.month) }, { it.title }),
    ).filter { (it.year ?: reign.startYear()) == selectedYear }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.95f)),
        border = BorderStroke(1.5.dp, Brass.copy(alpha = 0.8f)),
        shape = CutCornerShape(10.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Box(modifier = Modifier.heightIn(min = 430.dp)) {
            Image(
                painter = painterResource(R.drawable.timeline_mountain_ornament),
                contentDescription = null,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .height(125.dp),
                contentScale = ContentScale.FillWidth,
                alpha = 0.52f,
            )
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 14.dp, vertical = 18.dp),
                verticalArrangement = Arrangement.spacedBy(15.dp),
            ) {
                Text(
                    text = reign.yearLabel(selectedYear),
                    color = Vermilion,
                    fontFamily = FontFamily.Serif,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                )
                MonthLine(orderedEvents.map { it.month })
                Surface(
                    color = XuanPaper.copy(alpha = 0.72f),
                    shape = CutCornerShape(8.dp),
                    border = BorderStroke(1.dp, LineGold),
                ) {
                    if (orderedEvents.isEmpty()) {
                        EmptyYearState(reign = reign, selectedYear = selectedYear)
                    } else {
                        Column {
                            orderedEvents.forEachIndexed { index, event ->
                                val eventId = event.id.ifBlank { "${reign.title}:${event.title}" }
                                if (index > 0) HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
                                EventRow(
                                    event = event,
                                    tone = if (index == 0) Vermilion else Indigo,
                                    expanded = expandedEventId == eventId,
                                    onClick = { onEventClick(eventId) },
                                    onOpenPerson = onOpenPerson,
                                )
                            }
                        }
                    }
                }
                Spacer(Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun EmptyYearState(reign: Reign, selectedYear: Int) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 18.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("本年尚未编入导览事件", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Text(
            "${reign.yearLabel(selectedYear)} 的实录条目会随内容库校核后补入。",
            color = InkSoft,
            fontFamily = FontFamily.Serif,
            fontSize = 14.sp,
            textAlign = TextAlign.Center,
            lineHeight = 21.sp,
        )
    }
}

@Composable
private fun EventRow(
    event: HistoricalEvent,
    tone: Color,
    expanded: Boolean,
    onClick: () -> Unit,
    onOpenPerson: (String) -> Unit = {},
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Surface(shape = CutCornerShape(6.dp), color = tone) {
            Text(
                text = event.month,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 12.dp),
                color = PaperLight,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
            )
        }
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = event.title,
                    color = Ink,
                    modifier = Modifier.weight(1f),
                    fontFamily = FontFamily.Serif,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                )
                Icon(Icons.Outlined.LocationOn, event.place, modifier = Modifier.size(16.dp), tint = InkSoft)
                Text(event.place, color = InkSoft, fontSize = 13.sp)
            }
            Text(
                text = event.description,
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                lineHeight = 22.sp,
            )
            if (expanded) {
                HorizontalDivider(modifier = Modifier.padding(top = 5.dp), color = LineGold)
                Text(
                    text = event.detail,
                    color = Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 23.sp,
                )
                if (event.participants.isNotEmpty()) {
                    Row(
                        modifier = Modifier.padding(top = 5.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("相关人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
                        event.participants.forEach { name ->
                            Text(
                                text = name,
                                modifier = Modifier
                                    .clip(CutCornerShape(4.dp))
                                    .clickable { onOpenPerson(name) }
                                    .padding(horizontal = 6.dp, vertical = 3.dp),
                                color = Vermilion,
                                fontFamily = FontFamily.Serif,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }
                }
                if (event.consequence.isNotBlank()) {
                    Text(
                        text = "影响：${event.consequence}",
                        color = InkSoft,
                        fontFamily = FontFamily.Serif,
                        fontSize = 14.sp,
                        lineHeight = 21.sp,
                    )
                }
            }
        }
    }
}
