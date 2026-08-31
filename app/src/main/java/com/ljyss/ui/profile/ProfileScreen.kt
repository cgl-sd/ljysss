package com.ljyss.ui.profile

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.Composable
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle

@Composable
internal fun ProfileScreen(contentPadding: PaddingValues, onSearch: () -> Unit = {}) {
    MingList(contentPadding) {
        item { MingMasthead(onSearch) }
        item { OrnamentalTitle("我的") }
    }
}
