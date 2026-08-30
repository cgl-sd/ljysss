package com.ljyss.ui.timeline

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.Reign
import com.ljyss.domain.endYear
import com.ljyss.domain.startYear
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

@Composable
internal fun ReignRail(reigns: List<Reign>, selectedTitle: String, onSelected: (String) -> Unit) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        contentPadding = PaddingValues(horizontal = 3.dp),
    ) {
        items(reigns, key = { it.title }) { reign ->
            val selected = reign.title == selectedTitle
            Surface(
                modifier = Modifier
                    .widthIn(min = 62.dp)
                    .clip(CutCornerShape(5.dp))
                    .clickable { onSelected(reign.title) },
                color = if (selected) Vermilion else PaperLight,
                shape = CutCornerShape(5.dp),
                border = BorderStroke(1.dp, if (selected) Vermilion else LineGold),
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = reign.title,
                        color = if (selected) PaperLight else Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = reign.yearRange,
                        color = if (selected) PaperLight else InkSoft,
                        fontSize = 10.sp,
                    )
                }
            }
        }
    }
}

@Composable
internal fun DynastyRangeBar() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("1368", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 19.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = 10.dp),
            color = Brass,
            thickness = 2.dp,
        )
        Text("1644", color = Ink, fontFamily = FontFamily.Serif, fontSize = 19.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
internal fun ReignEventLine(reign: Reign) {
    val eventCountByYear = remember(reign) {
        reign.events.groupingBy { it.year ?: reign.startYear() }.eachCount()
    }
    val eventYears = eventCountByYear.keys.sorted()
    BoxWithConstraints(modifier = Modifier.fillMaxWidth().height(66.dp)) {
        val trackWidth = maxWidth - 36.dp
        val eventClusters = clusterEventYears(eventYears, reign.startYear(), reign.endYear(), trackWidth.value)
        HorizontalDivider(
            modifier = Modifier
                .align(Alignment.Center)
                .padding(horizontal = 18.dp),
            color = LineGold.copy(alpha = 0.78f),
            thickness = 1.dp,
        )
        eventClusters.forEach { cluster ->
            val year = cluster.years.average().toFloat()
            val fraction = if (reign.endYear() == reign.startYear()) 0.5f else
                (year - reign.startYear()) / (reign.endYear() - reign.startYear()).toFloat()
            TimelineEventMark(
                ordinalText = cluster.years.joinToString("·") { (it - reign.startYear() + 1).toString().padStart(2, '0') },
                eventCount = cluster.years.size,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(start = 18.dp)
                    .offset(x = (trackWidth * fraction) - 18.dp),
            )
        }
        Text(
            text = reign.startYear().toString(),
            modifier = Modifier.align(Alignment.BottomStart).padding(start = 18.dp),
            color = InkSoft,
            fontFamily = FontFamily.Serif,
            fontSize = 11.sp,
        )
        Text(
            text = reign.endYear().toString(),
            modifier = Modifier.align(Alignment.BottomEnd).padding(end = 18.dp),
            color = InkSoft,
            fontFamily = FontFamily.Serif,
            fontSize = 11.sp,
        )
    }
}

/** 固定年线：只让有史事的年份留下朱点；密集年份合并成一个带数量的节点。 */
@Composable
private fun TimelineEventMark(ordinalText: String, eventCount: Int, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.width(34.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = ordinalText,
            color = Vermilion,
            fontFamily = FontFamily.Monospace,
            fontSize = 8.sp,
            fontWeight = FontWeight.Bold,
        )
        Box(
            modifier = Modifier
                .padding(top = 8.dp)
                .size(if (eventCount > 1) 14.dp else 10.dp)
                .clip(RoundedCornerShape(50))
                .background(Vermilion),
            contentAlignment = Alignment.Center,
        ) {
            if (eventCount > 1) {
                Text(
                    text = eventCount.toString(),
                    color = PaperLight,
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

private data class EventYearCluster(val years: List<Int>)

/** 以屏幕上的最小间距合并相邻年份，防止洪武十三、十四年之类的标签相互覆盖。 */
private fun clusterEventYears(years: List<Int>, startYear: Int, endYear: Int, trackWidth: Float): List<EventYearCluster> {
    if (years.isEmpty()) return emptyList()
    val range = (endYear - startYear).coerceAtLeast(1).toFloat()
    val clusters = mutableListOf<MutableList<Int>>()
    years.forEach { year ->
        val previous = clusters.lastOrNull()
        val distance = previous?.lastOrNull()?.let { prior -> (year - prior) / range * trackWidth } ?: Float.MAX_VALUE
        if (previous != null && distance < 28f) previous += year else clusters += mutableListOf(year)
    }
    return clusters.map(::EventYearCluster)
}

@Composable
internal fun MonthLine(activeMonths: List<String>) {
    Row(modifier = Modifier.fillMaxWidth()) {
        listOf("正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "冬月", "腊月").forEach { month ->
            val active = activeMonths.contains(month)
            Column(
                modifier = Modifier.weight(1f),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                Text(
                    text = month.take(2),
                    color = if (active) Vermilion else InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 11.sp,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Normal,
                )
                Surface(
                    modifier = Modifier.size(if (active) 10.dp else 7.dp),
                    shape = RoundedCornerShape(50),
                    color = if (active) Vermilion else Brass,
                ) {}
            }
        }
    }
}
