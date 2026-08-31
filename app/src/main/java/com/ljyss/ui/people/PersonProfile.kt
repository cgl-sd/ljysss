package com.ljyss.ui.people

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.text.ClickableText
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
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.PersonSection
import com.ljyss.data.model.RelatedEvent
import com.ljyss.domain.LifeCollapseCharacterLimit
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
    onOpenPerson: (String) -> Unit,
    onOpenEvent: (String) -> Unit,
) {
    // 正常读取资料库预生成栏目；缺少 sections 时回退至摘要生平，
    // 不能让人物详情只剩姓名与画像。
    val sections = person.sections
        .ifEmpty {
            person.biography
                .takeIf { it.isNotBlank() }
                ?.let { listOf(PersonSection(key = "life", title = "生平", content = it, position = 0)) }
                .orEmpty()
        }
        .sortedBy { it.position }
    // 关系文章中出现的对方姓名保持可点击，跳转规则与旧的条目列表一致。
    val relationNames = relations
        .filter { (it.fromName == person.name || it.toName == person.name) && it.type !in parentChildTypes() }
        .map { if (it.fromName == person.name) it.toName else it.fromName }
        .distinct()

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
            PersonPortrait(person)
            Text(person.displayName, color = Ink, fontFamily = FontFamily.Serif, fontSize = 30.sp, fontWeight = FontWeight.Bold)
            Text(
                listOf(person.title, person.reign, person.years)
                    .filter { it.isNotBlank() }
                    .joinToString("｜"),
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                textAlign = TextAlign.Center,
            )
            sections.forEach { section ->
                val body = section.content
                if (body.isBlank() || body.contains("史料未见详载")) return@forEach
                when (section.key) {
                    "life" -> LifeSection(body)
                    "family" -> ProfileSection(section.title, readableParagraphs(body))
                    "relations" -> if (person.category != PersonCategory.EMPERORS) {
                        ArticleSection(section.title, body, relationNames, onOpenPerson)
                    }
                    // 相关事件只认 event_participant 的正式反链。旧正文来自早期自动抽取，
                    // 不能在无反链时回退展示，以免把无关的编年句误作人物经历。
                    "events" -> Unit
                    // 其余键属于内部标记（如资料状态），不作为栏目呈现。
                }
            }
            if (person.relatedEvents.isNotEmpty()) {
                RelatedEventsSection(person.relatedEvents, onOpenEvent)
            }
        }
    }
}

@Composable
private fun RelatedEventsSection(events: List<RelatedEvent>, onOpenEvent: (String) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text("相关事件", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            items(events, key = { it.id }) { event ->
                Card(
                    modifier = Modifier
                        .clip(CutCornerShape(5.dp))
                        .clickable { onOpenEvent(event.id) },
                    shape = CutCornerShape(5.dp),
                    border = BorderStroke(1.dp, Vermilion.copy(alpha = 0.65f)),
                    colors = CardDefaults.cardColors(containerColor = Vermilion.copy(alpha = 0.08f)),
                    elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
                ) {
                    Text(
                        text = "${event.year} · ${event.title}",
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                        color = Vermilion,
                        fontFamily = FontFamily.Serif,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

/** 生平栏目：维基长文按小标题分块，超长默认截断，可展开全文；《明史》原文块单独标色。 */
@Composable
private fun LifeSection(content: String) {
    val blocks = remember(content) { parseLifeBlocks(content) }
    var expanded by remember(content) { mutableStateOf(false) }
    val limit = LifeCollapseCharacterLimit
    val total = content.length
    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(7.dp)) {
        Text("生平", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        var used = 0
        var truncated = false
        for (block in blocks) {
            if (!expanded && used + block.text.length > limit) {
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
                    modifier = Modifier.padding(top = 1.dp),
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

/** 可点击人名的栏目文章：样式与 ProfileSection 一致，文中人名以朱色标出并可跳转。 */
@Composable
private fun ArticleSection(
    title: String,
    content: String,
    linkableNames: List<String>,
    onOpenPerson: (String) -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            readableParagraphs(content).forEach { paragraph ->
                val annotated = remember(paragraph, linkableNames) { annotateNames(paragraph, linkableNames) }
                ClickableText(
                    text = annotated,
                    onClick = { offset ->
                        annotated.getStringAnnotations("person", offset, offset)
                            .firstOrNull()
                            ?.let { onOpenPerson(it.item) }
                    },
                    style = TextStyle(
                        color = InkSoft,
                        fontFamily = FontFamily.Serif,
                        fontSize = 15.sp,
                        lineHeight = 26.sp,
                        textAlign = TextAlign.Justify,
                    ),
                )
            }
        }
    }
}

private fun annotateNames(text: String, names: List<String>): AnnotatedString =
    buildAnnotatedString {
        withStyle(SpanStyle(color = InkSoft)) { append(text) }
        names.filter { it.isNotBlank() }.sortedByDescending { it.length }.forEach { name ->
            var start = text.indexOf(name)
            while (start >= 0) {
                addStyle(SpanStyle(color = Vermilion), start, start + name.length)
                addStringAnnotation("person", name, start, start + name.length)
                start = text.indexOf(name, start + name.length)
            }
        }
    }
