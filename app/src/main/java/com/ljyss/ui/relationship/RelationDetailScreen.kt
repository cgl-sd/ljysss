package com.ljyss.ui.relationship

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
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.ui.components.MingEventLinks
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.RelatedEvent
import com.ljyss.ui.theme.Vermilion

/** 关系详情页：关系概要、局部关系图谱与两人共同参与的事件。 */
@Composable
internal fun RelationDetailScreen(
    relation: PersonRelation,
    relations: List<PersonRelation>,
    events: List<HistoricalEvent>,
    onOpenPerson: (String) -> Unit,
    onOpenEvent: (String) -> Unit,
) {
    val relationEnds = listOf(relation.fromName, relation.toName)
    val neighbors = relations
        .filter { it.fromName in relationEnds || it.toName in relationEnds }
        .map { if (it.fromName in relationEnds) it.toName else it.fromName }
        .distinct()
        .take(8)
    val focusNames = (relationEnds + neighbors).distinct()
    val focusRelations = relations.filter { it.fromName in focusNames && it.toName in focusNames }
    val sharedEvents = events
        .filter { relation.fromName in it.participants && relation.toName in it.participants }
        .sortedBy { it.year ?: Int.MAX_VALUE }

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
            Text(
                text = "${relation.fromName} · ${relation.type.label} · ${relation.toName}",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 27.sp,
                fontWeight = FontWeight.Bold,
            )
            Text(relation.reign, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 15.sp)
            if (relation.note.isNotBlank()) {
                Text(relation.note, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 21.sp)
            }
            Text("关系图谱", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
            RelationGraphCard(names = focusNames, relations = focusRelations, onOpenPerson = onOpenPerson)
            if (sharedEvents.isNotEmpty()) {
                Text("共同事件", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
                MingEventLinks(
                    events = sharedEvents.map { RelatedEvent(it.id, it.year ?: 0, it.title) },
                    onOpenEvent = onOpenEvent,
                )
            }
        }
    }
}
