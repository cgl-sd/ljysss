package com.ljyss.ui.people

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.domain.parseLifeBlocks
import com.ljyss.domain.parentChildTypes
import com.ljyss.domain.readableParagraphs
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

@Composable
internal fun PersonProfile(
    person: HistoricalPerson,
    relations: List<PersonRelation>,
    events: List<HistoricalEvent>,
    onBack: () -> Unit,
    onOpenPerson: (String) -> Unit,
) {
    val lifeSection = person.sections.firstOrNull { it.key == "life" }
    val familySection = person.sections.firstOrNull { it.key == "family" }
    val children = relations
        .filter { it.fromName == person.name && it.type in parentChildTypes() }
        .map { it.toName }
    val life = lifeSection?.content?.takeIf { it.isNotBlank() } ?: person.biography
    val family = familySection?.content?.takeIf { it.isNotBlank() }
        ?: listOf(person.familySummary, children.joinToString("、"))
            .filter { it.isNotBlank() }
            .joinToString("\n")
            .ifBlank { "家族、配偶与子嗣资料正在整理。" }
    // 关系与事件按人物交叉索引；没有记录时给出指向「关系」页的引导，避免空栏目。
    val personRelations = relations
        .filter { it.fromName == person.name || it.toName == person.name }
        .map { relation ->
            relation to (if (relation.fromName == person.name) relation.toName else relation.fromName)
        }
    val relatedEvents = events
        .filter { event -> event.participants.any { it == person.name } }
        .sortedBy { it.year ?: Int.MAX_VALUE }
        .map { event -> "${event.year?.toString() ?: "年份待考"} · ${event.title}\n${event.description}" }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(11.dp),
        ) {
            Text(
                "← 返回",
                modifier = Modifier
                    .align(Alignment.Start)
                    .clip(CutCornerShape(5.dp))
                    .clickable(onClick = onBack)
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium,
            )
            PersonPortrait(person)
            Text(person.name, color = Ink, fontFamily = FontFamily.Serif, fontSize = 30.sp, fontWeight = FontWeight.Bold)
            Text("${person.title}｜${person.reign}｜${person.years}", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 15.sp, textAlign = TextAlign.Center)
            LifeSection(life)
            // 没有实料的栏目不占位：家族占位文案、空关系、空事件均整栏隐藏。
            if (family.isNotBlank() && !family.contains("史料未见详载")) {
                ProfileSection("家族", readableParagraphs(family))
            }
            // 帝王条目不显示人物关系（宗室家庭资料在家族与子嗣栏呈现）。
            // 人物关系栏不含父子/母子（归家族栏）；帝王条目整栏不显示。
            val shownRelations = relations.filter {
                it.type !in parentChildTypes()
            }
            if (person.category != PersonCategory.EMPERORS && shownRelations.isNotEmpty()) {
                RelationSection(
                    shownRelations.map { relation ->
                        relation to (if (relation.fromName == person.name) relation.toName else relation.fromName)
                    },
                    onOpenPerson,
                )
            }
            if (relatedEvents.isNotEmpty()) {
                ProfileSection("相关事件", relatedEvents)
            }
        }
    }
}

/** 生平栏目：维基长文按小标题分块，超长默认截断，可展开全文；《明史》原文块单独标色。 */
@Composable
private fun LifeSection(content: String) {
    val blocks = remember(content) { parseLifeBlocks(content) }
    var expanded by remember(content) { mutableStateOf(false) }
    val limit = 1500
    val total = content.length
    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("生平", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        var used = 0
        var truncated = false
        for (block in blocks) {
            if (!expanded && used > limit) {
                truncated = true
                break
            }
            when {
                block.isClassicalMarker -> Text(
                    block.text,
                    modifier = Modifier.padding(top = 8.dp),
                    color = Brass,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                )
                block.isHeader -> Text(
                    block.text,
                    modifier = Modifier.padding(top = 7.dp),
                    color = Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                )
                else -> Text(
                    block.text,
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 26.sp,
                    textAlign = TextAlign.Justify,
                )
            }
            used += block.text.length
        }
        if (truncated) {
            Text(
                "展开全文（共 $total 字）",
                modifier = Modifier
                    .clip(CutCornerShape(5.dp))
                    .clickable { expanded = true }
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = Celadon,
                fontFamily = FontFamily.SansSerif,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
            )
        } else if (total > limit) {
            Text(
                "收起",
                modifier = Modifier
                    .clip(CutCornerShape(5.dp))
                    .clickable { expanded = false }
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = Brass,
                fontFamily = FontFamily.SansSerif,
                fontSize = 13.sp,
            )
        }
    }
}

@Composable
private fun ProfileSection(title: String, paragraphs: List<String>) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            paragraphs.forEach { paragraph ->
                Text(
                    text = paragraph,
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 26.sp,
                    textAlign = TextAlign.Justify,
                )
            }
        }
    }
}

/** 人物详情里的关系条目：点击任意一条即跳转到对方的人物详情。 */
@Composable
private fun RelationSection(relations: List<Pair<PersonRelation, String>>, onOpenPerson: (String) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text("人物关系", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        if (relations.isEmpty()) {
            Text(
                "暂无已编关系，可到「关系」页查看全量人物网络。",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                lineHeight = 26.sp,
            )
            return@Column
        }
        Text(
            "轻触条目，可跳转到对应人物",
            color = Brass,
            fontFamily = FontFamily.SansSerif,
            fontSize = 11.sp,
        )
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            relations.forEach { (relation, otherName) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(CutCornerShape(5.dp))
                        .clickable { onOpenPerson(otherName) }
                        .padding(horizontal = 4.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            "「${relation.type.label}」$otherName",
                            color = Ink,
                            fontFamily = FontFamily.Serif,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium,
                        )
                        if (relation.note.isNotBlank()) {
                            Text(
                                relation.note,
                                color = InkSoft,
                                fontFamily = FontFamily.Serif,
                                fontSize = 13.sp,
                                lineHeight = 20.sp,
                            )
                        }
                    }
                    Text(
                        "›",
                        color = Brass,
                        fontFamily = FontFamily.Serif,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}
