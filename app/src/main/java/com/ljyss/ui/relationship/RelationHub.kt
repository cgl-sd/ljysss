package com.ljyss.ui.relationship

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PersonRelation
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

/** 以人物为核心的关系卡片：整卡点击进入人物详情；关系行点击进入关系详情。 */
@Composable
internal fun RelationPersonCard(
    person: HistoricalPerson,
    rows: List<RelationRow>,
    onOpenPerson: (String) -> Unit,
    onOpenRelation: (PersonRelation) -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenPerson(person.name) },
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = person.displayName,
                    color = Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 19.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(person.title, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                Text(person.years, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
            }
            HorizontalDivider(color = LineGold.copy(alpha = 0.6f))
            rows.forEach { row ->
                RelationRowLine(row, onOpenRelation)
            }
        }
    }
}

/** 一条关系：类型色点＋类型名＋对方人物与说明。点击整行进入关系详情。 */
@Composable
private fun RelationRowLine(row: RelationRow, onOpenRelation: (PersonRelation) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenRelation(row.relation) }
            .padding(vertical = 4.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            Surface(modifier = Modifier.size(7.dp), shape = RoundedCornerShape(50), color = relationshipColor(row.relation.type)) {}
            Text(
                text = row.relation.type.label,
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 13.sp,
            )
            Text(
                text = row.otherName,
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(row.relation.reign, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 11.sp)
        }
        if (row.relation.note.isNotBlank()) {
            Text(
                text = row.relation.note,
                modifier = Modifier.padding(start = 14.dp),
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 12.sp,
                lineHeight = 17.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/** 人物关系卡片中的一行：以该人物为主视角的另一端人物与整条关系。 */
internal data class RelationRow(
    val otherName: String,
    val relation: PersonRelation,
)
