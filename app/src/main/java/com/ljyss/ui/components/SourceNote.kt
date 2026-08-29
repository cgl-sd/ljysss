package com.ljyss.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperShade

/** 史料出处与内容状态说明条。 */
@Composable
internal fun SourceNote(text: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(7.dp),
        color = PaperShade,
        border = BorderStroke(1.dp, LineGold),
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(14.dp),
            color = InkSoft,
            fontFamily = FontFamily.Serif,
            fontSize = 15.sp,
            lineHeight = 23.sp,
        )
    }
}
