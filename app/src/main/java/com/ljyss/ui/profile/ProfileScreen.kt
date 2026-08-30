package com.ljyss.ui.profile

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.Composable
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.components.SourceNote

@Composable
internal fun ProfileScreen(contentPadding: PaddingValues, onSearch: () -> Unit = {}) {
    MingList(contentPadding) {
        item { MingMasthead(onSearch) }
        item { OrnamentalTitle("我的") }
        item {
            SourceNote("历史资料以来源为先。未标卷次与出处的内容只作为导览，不作为定论。")
        }
    }
}
