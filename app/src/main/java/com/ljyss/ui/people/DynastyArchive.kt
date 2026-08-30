package com.ljyss.ui.people

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.Reign
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

@Composable
internal fun DynastyArchive(
    reign: Reign,
    people: List<HistoricalPerson>,
    onPersonSelected: (HistoricalPerson) -> Unit,
) {
    // 本朝人物按六分类全量归档：朝臣、将帅之外，宗藩、内廷、文苑与帝王同列，避免遗漏。
    val groups = PersonCategory.entries.map { category -> category to people.filter { it.category == category } }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.95f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("${reign.title}朝档案", color = Ink, fontFamily = FontFamily.Serif, fontSize = 25.sp, fontWeight = FontWeight.Bold)
            Text(reign.summary, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 23.sp)
            Text(
                "本朝已编 ${people.size} 人、${reign.events.size} 件大事；人物按六分类全量入档。",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
            )
            groups.forEach { (category, members) ->
                ArchiveGroup(category.label, category.subtitle, members, onPersonSelected)
            }
            Text("本朝大事", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            if (reign.events.isEmpty()) {
                Text("该朝事件正在按年份与史料卷次整理。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
            } else {
                reign.events.sortedBy { it.year ?: Int.MAX_VALUE }.forEach { event ->
                    Surface(
                        color = XuanPaper.copy(alpha = 0.68f),
                        shape = CutCornerShape(6.dp),
                        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.75f)),
                    ) {
                        Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text("${event.year ?: ""} ${event.month} · ${event.title}", color = Ink, fontFamily = FontFamily.Serif, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            Text(event.description, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 20.sp)
                            if (event.participants.isNotEmpty()) {
                                Text("相关人物：${event.participants.joinToString("、")}", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ArchiveGroup(
    title: String,
    hint: String,
    people: List<HistoricalPerson>,
    onPersonSelected: (HistoricalPerson) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.width(7.dp))
            Text(hint, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 12.sp)
        }
        if (people.isEmpty()) {
            Text("本朝暂无已编人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                items(people, key = { it.name }) { person ->
                    Surface(
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { onPersonSelected(person) },
                        shape = CutCornerShape(5.dp),
                        color = PaperShade,
                        border = BorderStroke(1.dp, LineGold),
                    ) {
                        Column(modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp)) {
                            Text(person.name, color = Ink, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                            Text(person.title, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}
