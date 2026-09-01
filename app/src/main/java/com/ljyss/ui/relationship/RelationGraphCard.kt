package com.ljyss.ui.relationship

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.RelationshipType
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Indigo
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper
import kotlin.math.cos
import kotlin.math.sin

/**
 * 详情页内嵌的只读关系图：节点均布圆周、无中心焦点，只画两端都在图内
 * 的关系边。人物与事件详情共用同一张图，避免再维护一份整页交互网络。
 */
@Composable
internal fun RelationGraphCard(
    names: List<String>,
    relations: List<PersonRelation>,
    onOpenPerson: (String) -> Unit,
) {
    val distinctNames = names.distinct()
    val graphHeight = when {
        distinctNames.size <= 1 -> 120.dp
        distinctNames.size <= 6 -> 240.dp
        else -> 320.dp
    }
    val scopedRelations = relations.filter { it.fromName in distinctNames && it.toName in distinctNames }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        BoxWithConstraints(
            modifier = Modifier
                .fillMaxWidth()
                .height(graphHeight)
                .clip(CutCornerShape(8.dp))
                .background(XuanPaper),
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val center = Offset(size.width / 2f, size.height / 2f)
                val centers = distinctNames.mapIndexed { index, name ->
                    val angle = -Math.PI / 2 + (Math.PI * 2 * index / distinctNames.size.coerceAtLeast(1))
                    name to Offset(
                        x = center.x + size.width * .39f * cos(angle).toFloat(),
                        y = center.y + size.height * .36f * sin(angle).toFloat(),
                    )
                }.toMap()
                scopedRelations.forEach { relation ->
                    val start = centers[relation.fromName] ?: return@forEach
                    val end = centers[relation.toName] ?: return@forEach
                    drawLine(
                        color = relationshipColor(relation.type).copy(alpha = .72f),
                        start = start,
                        end = end,
                        strokeWidth = 2.dp.toPx(),
                        cap = StrokeCap.Round,
                    )
                }
            }
            distinctNames.forEachIndexed { index, name ->
                val angle = -Math.PI / 2 + (Math.PI * 2 * index / distinctNames.size.coerceAtLeast(1))
                RelationshipNode(
                    name = name,
                    emphasized = false,
                    modifier = Modifier
                        .align(Alignment.TopStart)
                        .offset(
                            x = maxWidth / 2 + maxWidth * .39f * cos(angle).toFloat() - 30.dp,
                            y = maxHeight / 2 + maxHeight * .36f * sin(angle).toFloat() - 16.dp,
                        ),
                    onClick = { onOpenPerson(name) },
                )
            }
        }
    }
}

internal fun relationshipColor(type: RelationshipType): Color = when (type) {
    RelationshipType.RULER_MINISTER -> Vermilion
    RelationshipType.COMMAND -> Indigo
    RelationshipType.COLLEAGUE -> Brass
    RelationshipType.RIVAL -> InkSoft
    RelationshipType.MENTOR -> Celadon
    RelationshipType.PARENT_CHILD -> Vermilion
    RelationshipType.MOTHER_CHILD -> Vermilion
    RelationshipType.SPOUSE -> Celadon
    RelationshipType.SIBLING -> Brass
}

@Composable
internal fun RelationshipNode(
    name: String,
    emphasized: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit = {},
) {
    Surface(
        modifier = modifier.clickable(onClick = onClick),
        shape = CutCornerShape(5.dp),
        color = if (emphasized) Celadon else PaperLight,
        border = BorderStroke(1.dp, if (emphasized) Celadon else Brass),
    ) {
        Text(
            text = name,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp),
            color = if (emphasized) PaperLight else Ink,
            fontFamily = FontFamily.Serif,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
