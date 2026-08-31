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
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

/** 本朝大事的独立阅读页；档案卡不再在原位置展开。 */
@Composable
internal fun ArchiveEventProfile(event: HistoricalEvent, onOpenPerson: (String) -> Unit) {
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
            Text(
                listOfNotNull(event.year?.toString(), event.month.takeIf { it.isNotBlank() }, event.place.takeIf { it.isNotBlank() })
                    .joinToString("｜"),
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
            )
            if (event.sections.isEmpty()) {
                EventArticleSection("事件简介", event.description)
            } else {
                event.sections
                    .filter { it.key != "people" && it.content.isNotBlank() }
                    .sortedBy { it.position }
                    .forEach { section -> EventArticleSection(section.title, section.content) }
            }
            if (event.participants.isNotEmpty()) {
                Text("相关人物", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
                event.participants.forEach { name ->
                    Text(
                        name,
                        modifier = Modifier.clip(CutCornerShape(4.dp)).clickable { onOpenPerson(name) }.padding(vertical = 3.dp),
                        color = Vermilion,
                        fontFamily = FontFamily.Serif,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            if (event.sections.isEmpty()) {
                event.consequence.takeIf { it.isNotBlank() }?.let { EventArticleSection("影响", it) }
            }
            Text("出处：${event.sourceLabel}", color = Brass, fontFamily = FontFamily.Serif, fontSize = 13.sp)
        }
    }
}

@Composable
private fun EventArticleSection(title: String, content: String) {
    Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
    HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
    Text(content, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 26.sp)
}
