package com.ljyss.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

/** 四个页面共用的纸本列表容器：统一留白、行距与底部安全区。 */
@Composable
internal fun MingList(
    contentPadding: PaddingValues,
    content: LazyListScope.() -> Unit,
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(XuanPaper),
        contentPadding = PaddingValues(
            start = 18.dp,
            top = 44.dp,
            end = 18.dp,
            bottom = contentPadding.calculateBottomPadding() + 20.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        content = content,
    )
}

/** 页面题字：两侧横栏夹住标题，下方一枚菱形。 */
@Composable
internal fun OrnamentalTitle(title: String) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            HorizontalDivider(modifier = Modifier.width(72.dp), color = Brass.copy(alpha = 0.7f))
            Text(
                text = "  $title  ",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 29.sp,
                fontWeight = FontWeight.Bold,
            )
            HorizontalDivider(modifier = Modifier.width(72.dp), color = Brass.copy(alpha = 0.7f))
        }
        Text("◇", color = Vermilion, fontSize = 15.sp)
    }
}
