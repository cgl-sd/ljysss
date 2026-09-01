package com.ljyss.ui.relationship

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
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
import kotlin.math.sqrt

/**
 * 详情页内嵌的只读关系图：关联最多的人物居核心，其余人物环绕排列；
 * 关系边按类型着色并以弧线连接，底部给出类型图例。人物与事件详情共用。
 */
@Composable
internal fun RelationGraphCard(
    names: List<String>,
    relations: List<PersonRelation>,
    onOpenPerson: (String) -> Unit,
) {
    val distinctNames = names.distinct()
    val scopedRelations = relations.filter { it.fromName in distinctNames && it.toName in distinctNames }
    // 核心人物：图内关联边最多者；单人或空图时退化为首个名字。
    val focus = if (distinctNames.isEmpty()) null
    else distinctNames.maxByOrNull { name ->
        scopedRelations.count { it.fromName == name || it.toName == name }
    } ?: distinctNames.first()
    val others = distinctNames.filter { it != focus }
    val graphHeight = when {
        others.size <= 2 -> 240.dp
        others.size <= 8 -> 300.dp
        else -> 360.dp
    }
    val legendTypes = scopedRelations.map { it.type }.distinct()
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column {
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(graphHeight)
                    .clip(CutCornerShape(8.dp))
                    .background(XuanPaper),
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val center = Offset(size.width / 2f, size.height / 2f)
                    val canvasSize = size
                    val positions = buildMap {
                        focus?.let { put(it, center) }
                        others.forEachIndexed { index, name ->
                            val angle = -Math.PI / 2 + (Math.PI * 2 * index / others.size.coerceAtLeast(1))
                            put(
                                name,
                                Offset(
                                    x = center.x + canvasSize.width * .42f * cos(angle).toFloat(),
                                    y = center.y + canvasSize.height * .40f * sin(angle).toFloat(),
                                ),
                            )
                        }
                    }
                    scopedRelations.forEach { relation ->
                        val start = positions[relation.fromName] ?: return@forEach
                        val end = positions[relation.toName] ?: return@forEach
                        if (start == end) return@forEach
                        // 弧线：以线段中点的垂直偏移作为贝塞尔控制点，让连线有轻微弧度。
                        val mid = Offset((start.x + end.x) / 2f, (start.y + end.y) / 2f)
                        val dx = end.x - start.x
                        val dy = end.y - start.y
                        val len = sqrt(dx * dx + dy * dy).coerceAtLeast(1f)
                        val bend = 0.16f * len
                        val control = Offset(mid.x - dy / len * bend, mid.y + dx / len * bend)
                        val path = Path().apply {
                            moveTo(start.x, start.y)
                            quadraticBezierTo(control.x, control.y, end.x, end.y)
                        }
                        drawPath(
                            path = path,
                            color = relationshipColor(relation.type).copy(alpha = 0.82f),
                            style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round),
                        )
                    }
                }
                focus?.let { name ->
                    RelationshipNode(
                        name = name,
                        emphasized = true,
                        modifier = Modifier
                            .align(Alignment.Center)
                            .offset(x = (-30).dp, y = (-14).dp),
                        onClick = { onOpenPerson(name) },
                    )
                }
                others.forEachIndexed { index, name ->
                    val angle = -Math.PI / 2 + (Math.PI * 2 * index / others.size.coerceAtLeast(1))
                    RelationshipNode(
                        name = name,
                        emphasized = false,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .offset(
                                x = maxWidth * (.5f + .42f * cos(angle).toFloat()) - 30.dp,
                                y = maxHeight * (.5f + .40f * sin(angle).toFloat()) - 14.dp,
                            ),
                        onClick = { onOpenPerson(name) },
                    )
                }
            }
            if (legendTypes.isNotEmpty()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 9.dp),
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    legendTypes.forEach { type ->
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(5.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Surface(
                                modifier = Modifier.size(8.dp),
                                shape = RoundedCornerShape(50),
                                color = relationshipColor(type),
                            ) {}
                            Text(type.label, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                        }
                    }
                }
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
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 5.dp),
            color = if (emphasized) PaperLight else Ink,
            fontFamily = FontFamily.Serif,
            fontSize = if (emphasized) 13.sp else 12.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
