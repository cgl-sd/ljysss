package com.ljyss.ui.profile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.components.SourceNote
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

@Composable
internal fun ProfileScreen(contentPadding: PaddingValues) {
    MingList(contentPadding) {
        item { MingMasthead() }
        item { OrnamentalTitle("我的") }
        item {
            ProfileCard(
                title = "我的书案",
                description = "登录后可同步收藏、阅读进度与自建专题。",
                icon = Icons.Outlined.BookmarkBorder,
                action = "查看收藏",
            )
        }
        item {
            ProfileCard(
                title = "本地资料库",
                description = "人物、事件与分栏资料已随应用安装；无网络时也可完整阅读。",
                icon = Icons.Outlined.Download,
                action = "查看资料",
            )
        }
        item {
            SourceNote("历史资料以来源为先。未标卷次与出处的内容只作为导览，不作为定论。")
        }
    }
}

@Composable
private fun ProfileCard(title: String, description: String, icon: ImageVector, action: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, null, modifier = Modifier.size(34.dp), tint = Celadon)
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                Text(description, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 22.sp)
                Text(action, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
