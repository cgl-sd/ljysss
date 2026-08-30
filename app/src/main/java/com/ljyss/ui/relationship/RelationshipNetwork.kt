package com.ljyss.ui.relationship

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
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
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper
import kotlin.math.cos
import kotlin.math.sin

@Composable
internal fun RelationshipNetwork(relations: List<PersonRelation>) {
    val focusNames = remember(relations) {
        relations
            .flatMap { listOf(it.fromName, it.toName) }
            .distinct()
            .sorted()
    }
    val defaultFocus = remember(relations) {
        focusNames.maxByOrNull { name -> relations.count { it.fromName == name || it.toName == name } }.orEmpty()
    }
    var selectedFocus by rememberSaveable { mutableStateOf(defaultFocus) }
    val activeFocus = selectedFocus.takeIf { it in focusNames } ?: defaultFocus
    val focusedRelations = relations.filter { it.fromName == activeFocus || it.toName == activeFocus }
    val neighbours = focusedRelations.map { relation ->
        if (relation.fromName == activeFocus) relation.toName else relation.fromName
    }.distinct()
    val legend = focusedRelations.map { it.type }.distinct().map { it to it.label }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("人物关系图", color = Ink, fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
            Text(
                "按后端已编目的关系连线。选择一位人物，查看其直接关联；节点位置只为阅读布局，不代表地理位置或政治距离。",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                lineHeight = 21.sp,
            )
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(7.dp),
                contentPadding = PaddingValues(horizontal = 1.dp),
            ) {
                items(focusNames, key = { it }) { name ->
                    val selected = name == activeFocus
                    Surface(
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { selectedFocus = name },
                        shape = CutCornerShape(5.dp),
                        color = if (selected) Celadon else PaperShade,
                        border = BorderStroke(1.dp, if (selected) Celadon else LineGold),
                    ) {
                        Text(
                            text = name,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            color = if (selected) PaperLight else Ink,
                            fontFamily = FontFamily.Serif,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(if (neighbours.size > 6) 360.dp else 280.dp)
                    .clip(CutCornerShape(8.dp))
                    .background(XuanPaper),
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val center = androidx.compose.ui.geometry.Offset(size.width / 2f, size.height / 2f)
                    // 一位人物可与同一对象有多条关系。连线应按“对方姓名”取节点坐标，
                    // 不能把关系序号当成去重后的节点序号，否则会越界并导致关系页崩溃。
                    val neighbourCenters = neighbours.mapIndexed { index, name ->
                        val angle = -Math.PI / 2 + (Math.PI * 2 * index / neighbours.size.coerceAtLeast(1))
                        name to androidx.compose.ui.geometry.Offset(
                            x = center.x + size.width * .39f * cos(angle).toFloat(),
                            y = center.y + size.height * .36f * sin(angle).toFloat(),
                        )
                    }.toMap()
                    focusedRelations.forEach { relation ->
                        val otherName = if (relation.fromName == activeFocus) relation.toName else relation.fromName
                        val endpoint = neighbourCenters.getValue(otherName)
                        drawLine(
                            color = relationshipColor(relation.type).copy(alpha = .72f),
                            start = center,
                            end = endpoint,
                            strokeWidth = if (relation.type == RelationshipType.RULER_MINISTER) 3.dp.toPx() else 2.dp.toPx(),
                            cap = StrokeCap.Round,
                        )
                    }
                }
                RelationshipNode(
                    name = activeFocus,
                    emphasized = true,
                    modifier = Modifier.align(Alignment.Center),
                )
                neighbours.forEachIndexed { index, name ->
                    val angle = -Math.PI / 2 + (Math.PI * 2 * index / neighbours.size.coerceAtLeast(1))
                    RelationshipNode(
                        name = name,
                        emphasized = false,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .offset(
                                x = maxWidth / 2 + maxWidth * .39f * cos(angle).toFloat() - 30.dp,
                                y = maxHeight / 2 + maxHeight * .36f * sin(angle).toFloat() - 16.dp,
                            ),
                    )
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                legend.forEach { (type, label) ->
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                        Surface(modifier = Modifier.size(8.dp), shape = RoundedCornerShape(50), color = relationshipColor(type)) {}
                        Text(label, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                    }
                }
            }
            Text(
                "已建立 ${relations.size} 条首批关系；当前显示“$activeFocus”关联的 ${focusedRelations.size} 条，可横向选择其他人物继续查看。",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 13.sp,
            )
        }
    }
}

private fun relationshipColor(type: RelationshipType): Color = when (type) {
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
internal fun RelationshipNode(name: String, emphasized: Boolean, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
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

/** 关系页的双视图：人物关系网络与事件关系网络。 */
internal enum class RelationView(val label: String) {
    PERSON("人物关系"),
    EVENT("事件关系"),
}

@Composable
internal fun RelationViewRail(selected: RelationView, onSelected: (RelationView) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        RelationView.entries.forEach { view ->
            val active = view == selected
            Surface(
                modifier = Modifier
                    .clip(CutCornerShape(6.dp))
                    .clickable { onSelected(view) },
                shape = CutCornerShape(6.dp),
                color = if (active) Vermilion else PaperLight,
                border = BorderStroke(1.dp, if (active) Vermilion else LineGold),
            ) {
                Text(
                    text = view.label,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 9.dp),
                    color = if (active) PaperLight else Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

/** 事件为中心的辐射图：辐条一端是参与人物，另一端是共享人物的其他事件。 */
