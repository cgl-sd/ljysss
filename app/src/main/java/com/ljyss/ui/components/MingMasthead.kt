package com.ljyss.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Search
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.R
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

/** 书眉：以较小的藏书题签统摄四页，避免与各页主标题争夺视觉重心。 */
@Composable
internal fun MingMasthead(onSearch: (() -> Unit)? = null) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Image(
            painter = painterResource(R.drawable.ding_map_emblem),
            contentDescription = "两京一十三省的鼎形图标",
            modifier = Modifier.size(32.dp),
            contentScale = ContentScale.Fit,
        )
        Spacer(Modifier.width(8.dp))
        Column {
            Text(
                text = "两京一十三省",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.2.sp,
            )
            Text(
                text = "明代历史图录",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 9.sp,
                letterSpacing = 1.6.sp,
            )
        }
        if (onSearch != null) {
            Spacer(Modifier.weight(1f))
            IconButton(onClick = onSearch, modifier = Modifier.size(36.dp)) {
                Icon(
                    Icons.Outlined.Search,
                    contentDescription = "全局搜索",
                    tint = Vermilion,
                )
            }
        }
    }
}

/** 朱文印章：仅用于资料卡的分类标记，不再挤占书眉。 */
@Composable
internal fun Seal(text: String) {
    Surface(shape = CutCornerShape(4.dp), color = Vermilion) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp),
            color = PaperLight,
            fontFamily = FontFamily.Serif,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
