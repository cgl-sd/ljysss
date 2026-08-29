package com.ljyss.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
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

/** 书眉：鼎形图标、书名与「集录」朱印。 */
@Composable
internal fun MingMasthead() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Image(
            painter = painterResource(R.drawable.ding_map_emblem),
            contentDescription = "两京一十三省的鼎形图标",
            modifier = Modifier.size(38.dp),
            contentScale = ContentScale.Fit,
        )
        Spacer(Modifier.width(9.dp))
        Text(
            text = "两京一十三省",
            color = Ink,
            fontFamily = FontFamily.Serif,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp,
        )
        Spacer(Modifier.width(9.dp))
        Seal("集录")
    }
}

/** 朱文印章：栏目分类与书名旁的小红块。 */
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
