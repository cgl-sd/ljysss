package com.ljyss.ui.timeline

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

@Composable
internal fun ReignRail(reigns: List<Reign>, selectedTitle: String, onSelected: (String) -> Unit) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(horizontal = 2.dp),
    ) {
        items(reigns, key = { it.title }) { reign ->
            val selected = reign.title == selectedTitle
            Surface(
                modifier = Modifier
                    .widthIn(min = 74.dp)
                    .clip(CutCornerShape(8.dp))
                    .clickable { onSelected(reign.title) },
                color = if (selected) Vermilion else PaperLight,
                shape = CutCornerShape(8.dp),
                border = BorderStroke(1.dp, if (selected) Vermilion else LineGold),
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = reign.title,
                        color = if (selected) PaperLight else Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = reign.yearRange.substringBefore("—"),
                        color = if (selected) PaperLight else InkSoft,
                        fontSize = 11.sp,
                    )
                }
            }
        }
    }
}

@Composable
internal fun ReignYearRail(reign: Reign, selectedYear: Int, onSelected: (Int) -> Unit) {
    val eventCountByYear = remember(reign) {
        reign.events.groupingBy { it.year ?: reign.startYear() }.eachCount()
    }
    Box(modifier = Modifier.fillMaxWidth().height(52.dp)) {
        HorizontalDivider(
            modifier = Modifier
                .align(Alignment.Center)
                .padding(horizontal = 18.dp),
            color = LineGold.copy(alpha = 0.78f),
            thickness = 1.dp,
        )
        LazyRow(
            modifier = Modifier.fillMaxSize(),
            horizontalArrangement = Arrangement.spacedBy(3.dp),
            contentPadding = PaddingValues(horizontal = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            items((reign.startYear()..reign.endYear()).toList(), key = { it }) { year ->
                val selected = year == selectedYear
                val eventCount = eventCountByYear[year] ?: 0
                val sequence = (year - reign.startYear() + 1).toString().padStart(2, '0')
                Column(
                    modifier = Modifier
                        .width(34.dp)
                        .fillMaxSize()
                        .clickable { onSelected(year) },
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text(
                        text = sequence,
                        color = if (selected) Celadon else InkSoft,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Surface(
                        modifier = Modifier.size(if (selected) 13.dp else if (eventCount > 0) 8.dp else 5.dp),
                        shape = RoundedCornerShape(50),
                        color = when {
                            selected -> Celadon
                            eventCount > 0 -> Vermilion
                            else -> Brass
                        },
                    ) {}
                    Text(
                        text = if (selected) "$year" else "",
                        color = InkSoft,
                        fontFamily = FontFamily.Serif,
                        fontSize = 9.sp,
                    )
                }
            }
        }
    }
}
