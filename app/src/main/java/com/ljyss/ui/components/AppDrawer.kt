package com.ljyss.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.R
import com.ljyss.data.UpdateSource
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

/** 左上角书眉弹出的侧栏：分列页面入口与应用更新。 */
@Composable
internal fun AppDrawerContent(
    sectionLabels: List<String>,
    selectedSection: Int,
    onSectionSelected: (Int) -> Unit,
    updateSource: UpdateSource,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(0.86f).fillMaxHeight(),
        color = XuanPaper,
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.6f)),
    ) {
        Column(
            modifier = Modifier
                .statusBarsPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Image(
                    painter = painterResource(R.drawable.ding_map_emblem),
                    contentDescription = "两京一十三省的鼎形图标",
                    modifier = Modifier.size(34.dp),
                    contentScale = ContentScale.Fit,
                )
                Spacer(Modifier.width(10.dp))
                Column {
                    Text("两京一十三省", color = Ink, fontFamily = FontFamily.Serif, fontSize = 19.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
                    Text("明代历史图录", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 9.sp, letterSpacing = 1.6.sp)
                }
            }
            HorizontalDivider(color = LineGold.copy(alpha = 0.72f), thickness = 1.dp)
            sectionLabels.forEachIndexed { index, label ->
                val selected = index == selectedSection
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(CutCornerShape(6.dp))
                        .clickable { onSectionSelected(index) }
                        .padding(horizontal = 12.dp, vertical = 11.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("◇", color = if (selected) Vermilion else LineGold, fontSize = 11.sp, modifier = Modifier.width(20.dp))
                    Text(label, color = if (selected) Vermilion else Ink, fontFamily = FontFamily.Serif, fontSize = 16.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium)
                }
            }
            HorizontalDivider(color = LineGold.copy(alpha = 0.72f), thickness = 1.dp)
                        AppUpdateEntry(updateSource = updateSource)
        }
    }
}
