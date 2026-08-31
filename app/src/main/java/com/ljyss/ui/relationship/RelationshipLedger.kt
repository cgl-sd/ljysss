package com.ljyss.ui.relationship

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.PersonRelation
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

/** 关系图下方的可核对清单；只记录人物与人物之间的关系。 */
@Composable
internal fun RelationshipLedger(relations: List<PersonRelation>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column {
            Row(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("关系簿", color = Ink, modifier = Modifier.weight(1f), fontFamily = FontFamily.Serif, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text("按时代标注", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
            }
            relations.forEachIndexed { index, relation ->
                if (index > 0) HorizontalDivider(color = LineGold.copy(alpha = .65f))
                Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = "${relation.fromName}  ·  ${relation.type.label}  ·  ${relation.toName}",
                        color = Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text("${relation.reign}｜${relation.note}", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 21.sp)
                }
            }
        }
    }
}
