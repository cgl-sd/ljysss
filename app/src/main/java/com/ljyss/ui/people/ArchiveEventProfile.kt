package com.ljyss.ui.people

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.PersonRelation
import com.ljyss.ui.components.MingArticleSection
import com.ljyss.ui.components.MingPersonLinks
import com.ljyss.ui.relationship.RelationGraphCard
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

/** 正文折叠阈值：超过即收起并给出"展开全文"。 */
private const val EventSectionCharacterLimit = 900

/** 相关人物默认展示上限；超出后提供"展开全部"。 */
private const val EventParticipantsCollapseLimit = 12

/** 本朝大事的独立阅读页；档案卡不再在原位置展开。 */
@Composable
internal fun ArchiveEventProfile(event: HistoricalEvent, relations: List<PersonRelation>, onOpenPerson: (String) -> Unit) {
    // 每个正文分栏独立记忆展开状态（key 用 section 标题）。
    val expandedSections = remember(event) { mutableStateOf(setOf<String>()) }
    var participantsExpanded by remember(event) { mutableStateOf(false) }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(event.title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 27.sp, fontWeight = FontWeight.Bold)
            val yearLabel = event.year?.let { start ->
                val end = event.endYear
                if (end != null && end != start) "$start—$end" else start.toString()
            }
            Text(
                listOfNotNull(
                    yearLabel,
                    event.month.takeIf { it.isNotBlank() },
                    event.eventType.takeIf { it.isNotBlank() && it != "未分类" },
                    event.place.takeIf { it.isNotBlank() },
                )
                    .joinToString("｜"),
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
            )
            if (event.sections.isEmpty()) {
                EventArticleSection("事件简介", event.description, expandedSections)
            } else {
                event.sections
                    .filter { it.key != "people" && it.content.isNotBlank() }
                    .sortedBy { it.position }
                    .forEach { section ->
                        EventArticleSection(section.title, section.content, expandedSections)
                    }
            }
            if (event.participants.isNotEmpty()) {
                Text("相关人物", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
                val distinctParticipants = event.participants.filter { it.isNotBlank() }.distinct()
                val shown = if (participantsExpanded || distinctParticipants.size <= EventParticipantsCollapseLimit) {
                    distinctParticipants
                } else {
                    distinctParticipants.take(EventParticipantsCollapseLimit)
                }
                MingPersonLinks(shown, onOpenPerson)
                if (!participantsExpanded && distinctParticipants.size > EventParticipantsCollapseLimit) {
                    Text(
                        "展开全部（共 ${distinctParticipants.size} 人）",
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { participantsExpanded = true }
                            .padding(horizontal = 4.dp, vertical = 6.dp),
                        color = Celadon,
                        fontFamily = FontFamily.SansSerif,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                    )
                }
            }
            // 人物关系：只画该事件参与人之间的直接关系，共同经历即连线依据。
            if (event.participants.size >= 2) {
                val eventRelations = relations.filter {
                    it.fromName in event.participants && it.toName in event.participants
                }
                Text("人物关系", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
                RelationGraphCard(names = event.participants.distinct(), relations = eventRelations, onOpenPerson = onOpenPerson)
            }
            if (event.sections.isEmpty()) {
                event.consequence.takeIf { it.isNotBlank() }?.let { EventArticleSection("影响", it, expandedSections) }
            }
        }
    }
}

/** 事件正文分栏：超长默认收起，可展开全文；与人物"生平"的折叠交互保持一致。 */
@Composable
private fun EventArticleSection(title: String, content: String, expandedSections: androidx.compose.runtime.MutableState<Set<String>>) {
    val expanded = title in expandedSections.value
    val limit = EventSectionCharacterLimit
    val truncated = !expanded && content.length > limit
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            val shownContent = if (truncated) content.take(limit) else content
            com.ljyss.domain.readableParagraphs(shownContent).forEach { paragraph ->
                Text(
                    paragraph,
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 26.sp,
                )
            }
        }
        if (truncated) {
            Text(
                "展开全文（共 ${content.length} 字）",
                modifier = Modifier
                    .clip(CutCornerShape(5.dp))
                    .clickable { expandedSections.value = expandedSections.value + title }
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = Celadon,
                fontFamily = FontFamily.SansSerif,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
            )
        } else if (content.length > limit) {
            Text(
                "收起",
                modifier = Modifier
                    .clip(CutCornerShape(5.dp))
                    .clickable { expandedSections.value = expandedSections.value - title }
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = Brass,
                fontFamily = FontFamily.SansSerif,
                fontSize = 13.sp,
            )
        }
    }
}
