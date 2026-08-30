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
import androidx.compose.material3.HorizontalDivider
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
private val ArchivePersonCardWidth = 100.dp
private val ArchivePersonCardHeight = 54.dp

@Composable
internal fun DynastyArchive(
    reign: Reign,
    people: List<HistoricalPerson>,
    expandedEventId: String?,
    onPersonSelected: (HistoricalPerson) -> Unit,
    onOpenPerson: (String) -> Unit,
    onEventSelected: (HistoricalEvent) -> Unit,
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
                ArchiveGroup(category.label, members, onPersonSelected)
            }
            Text("本朝大事", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            if (reign.events.isEmpty()) {
                Text("该朝事件正在按年份与史料卷次整理。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
            } else {
                reign.events.sortedBy { it.year ?: Int.MAX_VALUE }.forEach { event ->
                    val eventId = event.id.ifBlank { "${reign.title}:${event.title}" }
                    ArchiveEventCard(
                        event = event,
                        expanded = expandedEventId == eventId,
                        onClick = { onEventSelected(event) },
                        onOpenPerson = onOpenPerson,
                    )
                }
            }
        }
    }
}

/** 收起时三项信息同高展示；展开后保留完整叙述，避免用截断替代事件详情。 */
@Composable
private fun ArchiveEventCard(
    event: HistoricalEvent,
    expanded: Boolean,
    onClick: () -> Unit,
    onOpenPerson: (String) -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .then(if (expanded) Modifier else Modifier.height(ArchiveEventCardHeight))
            .clip(CutCornerShape(6.dp))
            .clickable(onClick = onClick),
        color = XuanPaper.copy(alpha = 0.68f),
        shape = CutCornerShape(6.dp),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.75f)),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
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
                lineHeight = 20.sp,
                maxLines = if (expanded) Int.MAX_VALUE else 2,
                overflow = if (expanded) TextOverflow.Clip else TextOverflow.Ellipsis,
            )
            ArchiveParticipants(event.participants, onOpenPerson)
            if (expanded) {
                HorizontalDivider(modifier = Modifier.padding(top = 4.dp), color = LineGold.copy(alpha = 0.75f))
                Text(
                    event.detail.takeIf { it.isNotBlank() && it != event.description }
                        ?: "详细叙述正在依据史料继续整理。",
                    color = Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 23.sp,
                )
                Text("出处：${event.sourceLabel}", color = Brass, fontFamily = FontFamily.Serif, fontSize = 13.sp)
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
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        }
        if (people.isEmpty()) {
            Text("本朝暂无已编人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                items(people, key = { it.name }) { person ->
                    Surface(
                        modifier = Modifier
                            .width(ArchivePersonCardWidth)
                            .height(ArchivePersonCardHeight)
                            .clip(CutCornerShape(5.dp))
                            .clickable { onPersonSelected(person) },
                        shape = CutCornerShape(5.dp),
                        color = PaperShade,
                        border = BorderStroke(1.dp, LineGold),
                    ) {
                        Column(modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp)) {
                            Text(
                                person.name,
                                color = Ink,
                                fontFamily = FontFamily.Serif,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            archiveRoleLabel(person).takeIf { it.isNotBlank() }?.let { role ->
                                Text(
                                    role,
                                    color = InkSoft,
                                    fontFamily = FontFamily.Serif,
                                    fontSize = 11.sp,
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
}

/** 朝代档案只显示一个可辨认的职位或爵位，完整称谓仍保留在详情页。 */
private fun archiveRoleLabel(person: HistoricalPerson): String {
    val title = person.title.trim()
    if (title.isBlank()) return ""
    if (person.category == PersonCategory.EMPERORS) {
        return title.removePrefix("明").substringBefore('·').ifBlank { "皇帝" }
    }
    if (person.category == PersonCategory.COURT) {
        Regex("(皇后|皇贵妃|贵妃|[贤淑宁德惠恭顺庄端孝]+妃|妃|嫔|太监)$")
            .find(title)
            ?.value
            ?.let { return it }
    }

    val titleParts = title.split(Regex("[、，；;]|兼|（|\\("))
        .map { it.trim() }
        .filter { it.isNotBlank() }
    val officeKeywords = listOf(
        "首辅", "大学士", "尚书", "侍郎", "都御史", "总督", "巡抚", "督师", "都督",
        "将军", "指挥使", "御史", "给事中", "布政使", "按察使", "知府", "知县", "祭酒", "学士",
    )
    titleParts.firstOrNull { part -> officeKeywords.any(part::contains) }
        ?.let { return it }
    titleParts.firstOrNull { part -> part.endsWith("王") || part.endsWith("公") || part.endsWith("侯") || part.endsWith("伯") }
        ?.let { return it }
    val fallback = titleParts.firstOrNull()?.removePrefix("明·")?.removePrefix("明代").orEmpty()
    return fallback.takeUnless { it.isBlank() || it == person.name || it == "官员" }
        .orEmpty()
}
