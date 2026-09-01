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

/** 关系页按朝代分组的小标题：朝代名＋人物数。 */
@Composable
internal fun RelationDynastyHeader(title: String, personCount: Int) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 18.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        HorizontalDivider(modifier = Modifier.width(28.dp), color = Vermilion)
        Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Text("${personCount} 人", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 13.sp)
    }
    HorizontalDivider(modifier = Modifier.padding(bottom = 8.dp), color = LineGold.copy(alpha = .65f))
}

/** 以人物为核心的关系卡片：人物名＋称号＋纪年，下面列出与其直接相关的人物与关系类型。 */
@Composable
internal fun RelationPersonCard(
    person: HistoricalPerson,
    rows: List<RelationRow>,
    onOpenPerson: (String) -> Unit,
    onOpenRelation: (PersonRelation) -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = person.displayName,
                    modifier = Modifier.clickable { onOpenPerson(person.name) },
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

/** 一条关系：类型色点＋类型名＋对方人物。点击进入关系详情。 */
@Composable
private fun RelationRowLine(row: RelationRow, onOpenRelation: (PersonRelation) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenRelation(row.relation) }
            .padding(vertical = 4.dp),
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
            fontSize = 15.sp,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(row.relation.reign, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 11.sp)
    }
    if (row.relation.note.isNotBlank()) {
        Text(
            text = row.relation.note,
            modifier = Modifier.padding(start = 14.dp, bottom = 2.dp),
            color = InkSoft,
            fontFamily = FontFamily.Serif,
            fontSize = 12.sp,
            lineHeight = 17.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** 人物关系卡片中的一行：以该人物为主视角的另一端人物与整条关系。 */
internal data class RelationRow(
    val otherName: String,
    val relation: PersonRelation,
)
