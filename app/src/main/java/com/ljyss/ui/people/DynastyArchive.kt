package com.ljyss.ui.people

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxHeight
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
import com.ljyss.domain.orderedPeopleForCards
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

private val ArchiveEventCardHeight = 116.dp
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
        category to orderedPeopleForCards(people.filter { it.category == category }, reign.title)
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
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("${reign.title}朝档案", modifier = Modifier.weight(1f), color = Ink, fontFamily = FontFamily.Serif, fontSize = 25.sp, fontWeight = FontWeight.Bold)
                Surface(shape = CutCornerShape(4.dp), color = Vermilion) {
                    Text("朝档", modifier = Modifier.padding(horizontal = 7.dp, vertical = 4.dp), color = PaperLight, fontFamily = FontFamily.Serif, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }
            Text(reign.summary, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 23.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ArchiveStat("本朝已编", "${people.size} 人", Modifier.weight(1f))
                ArchiveStat("本朝大事", "${reign.events.size} 件", Modifier.weight(1f))
            }
            groups.forEach { (category, members) ->
                ArchiveGroup(category.label, members, onPersonSelected)
            }
            ArchiveSectionHeading("本朝大事")
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

@Composable
private fun ArchiveStat(label: String, value: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = CutCornerShape(5.dp),
        color = PaperShade.copy(alpha = 0.48f),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.78f)),
    ) {
        Column(modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(value, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Text(label, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 11.sp)
        }
    }
}

@Composable
private fun ArchiveSectionHeading(title: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Box(modifier = Modifier.padding(start = 9.dp).weight(1f).height(1.dp).background(LineGold.copy(alpha = 0.72f)))
        Text("◇", modifier = Modifier.padding(start = 7.dp), color = Vermilion, fontSize = 13.sp)
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
        Row {
            Box(modifier = Modifier.width(3.dp).fillMaxHeight().background(Vermilion.copy(alpha = 0.82f)))
            Column(
                modifier = Modifier.weight(1f).padding(horizontal = 11.dp, vertical = 9.dp),
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
        ArchiveSectionHeading(title)
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
