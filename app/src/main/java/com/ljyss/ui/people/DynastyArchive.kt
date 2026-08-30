package com.ljyss.ui.people

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.Reign
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

private val ArchiveEventCardHeight = 108.dp
private val ArchivePersonCardWidth = 78.dp
private val ArchivePersonCardHeight = 55.dp

@Composable
internal fun DynastyArchive(
    reign: Reign,
    people: List<HistoricalPerson>,
    onPersonSelected: (HistoricalPerson) -> Unit,
    onOpenPerson: (String) -> Unit,
    onEventSelected: (HistoricalEvent) -> Unit,
) {
    val groups = PersonCategory.entries.map { category ->
        category to archiveOrderedPeople(category, people.filter { it.category == category })
    }

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
                "本朝已编 ${people.size} 人，${reign.events.size} 件大事",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
            )
            groups.forEach { (category, members) ->
                ArchiveGroup(category.label, members, onPersonSelected)
            }
            Text("本朝大事", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            if (reign.events.isEmpty()) {
                Text("该朝事件正在按年份与史料卷次整理。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
            } else {
                reign.events.sortedBy { it.year ?: Int.MAX_VALUE }.forEach { event ->
                    ArchiveEventCard(
                        event = event,
                        onClick = { onEventSelected(event) },
                        onOpenPerson = onOpenPerson,
                    )
                }
            }
        }
    }
}

/** 档案卡只承担入口职责；完整介绍在独立事件页阅读。 */
@Composable
private fun ArchiveEventCard(
    event: HistoricalEvent,
    onClick: () -> Unit,
    onOpenPerson: (String) -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .height(ArchiveEventCardHeight)
            .clip(CutCornerShape(6.dp))
            .clickable(onClick = onClick),
        color = XuanPaper.copy(alpha = 0.68f),
        shape = CutCornerShape(6.dp),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.75f)),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 9.dp, vertical = 7.dp),
            verticalArrangement = Arrangement.spacedBy(3.dp),
        ) {
            Text(
                "${event.year ?: ""} ${event.month} · ${event.title.ifBlank { "事件待补题" }}",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                "简介：${event.description.ifBlank { "事件简介正在整理。" }}",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                lineHeight = 18.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            ArchiveParticipants(event.participants, onOpenPerson)
        }
    }
}

@Composable
private fun ArchiveParticipants(participants: List<String>, onOpenPerson: (String) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text("相关人物：", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
        if (participants.isEmpty()) {
            Text("待补充", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 13.sp)
        } else {
            LazyRow(
                modifier = Modifier.weight(1f),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(participants, key = { it }) { name ->
                    Text(
                        name,
                        modifier = Modifier
                            .clip(CutCornerShape(4.dp))
                            .clickable { onOpenPerson(name) }
                            .padding(horizontal = 2.dp, vertical = 2.dp),
                        color = Vermilion,
                        fontFamily = FontFamily.Serif,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun ArchiveGroup(
    title: String,
    people: List<HistoricalPerson>,
    onPersonSelected: (HistoricalPerson) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        }
        if (people.isEmpty()) {
            Text("本朝暂无已编人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                items(people, key = { it.name }) { person ->
                    Surface(
                        modifier = Modifier.width(ArchivePersonCardWidth).height(ArchivePersonCardHeight)
                            .clip(CutCornerShape(5.dp))
                            .clickable { onPersonSelected(person) },
                        shape = CutCornerShape(5.dp),
                        color = PaperShade,
                        border = BorderStroke(1.dp, LineGold),
                    ) {
                        Column(modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp)) {
                            Text(
                                person.displayName,
                                color = Ink,
                                fontFamily = FontFamily.Serif,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                archiveRoleLabel(person),
                                color = InkSoft,
                                fontFamily = FontFamily.Serif,
                                fontSize = 10.sp,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                }
            }
        }
    }
}

private fun archiveRoleLabel(person: HistoricalPerson): String = person.title

private fun archiveOrderedPeople(category: PersonCategory, people: List<HistoricalPerson>): List<HistoricalPerson> =
    people.sortedWith(compareBy<HistoricalPerson>(
        { archiveRank(category, it) },
        { it.reign },
        { it.years.substringBefore('—').toIntOrNull() ?: Int.MAX_VALUE },
        { it.displayName },
    ))

private fun archiveRank(category: PersonCategory, person: HistoricalPerson): Int = when (category) {
    PersonCategory.COURT -> when {
        person.title.contains("皇后") || person.title.contains("太后") -> 0
        person.title.contains("妃") || person.title.contains("嫔") || person.title.contains("选侍") -> 1
        else -> 2
    }
    PersonCategory.CLAN -> when {
        person.title.contains("亲王") || person.title.matches(Regex(".{1,8}王")) -> 0
        person.title.contains("郡王") -> 1
        person.title.contains("世子") -> 2
        person.title.contains("公主") -> 4
        else -> 3
    }
    else -> 0
}
