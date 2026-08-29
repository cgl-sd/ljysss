package com.ljyss.ui.timeline

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import com.ljyss.data.MingRepository
import com.ljyss.domain.startYear
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle

@Composable
internal fun TimelineScreen(
    repository: MingRepository,
    contentPadding: PaddingValues,
    onOpenPerson: (String) -> Unit = {},
) {
    val reigns = remember(repository) { repository.reigns() }
    var selectedTitle by rememberSaveable { mutableStateOf(reigns.first().title) }
    var selectedYear by rememberSaveable { mutableIntStateOf(reigns.first().startYear()) }
    var expandedEventId by rememberSaveable { mutableStateOf<String?>(null) }
    val selectedReign = reigns.first { it.title == selectedTitle }

    MingList(contentPadding) {
        item { MingMasthead() }
        item { OrnamentalTitle("岁月") }
        item {
            ReignRail(reigns, selectedTitle) {
                selectedTitle = it
                selectedYear = reigns.first { reign -> reign.title == it }.startYear()
                expandedEventId = null
            }
        }
        item {
            ReignYearRail(
                reign = selectedReign,
                selectedYear = selectedYear,
                onSelected = {
                    selectedYear = it
                    expandedEventId = null
                },
            )
        }
        item { DynastyRangeBar() }
        item {
            TimelineArchive(
                reign = selectedReign,
                selectedYear = selectedYear,
                expandedEventId = expandedEventId,
                onOpenPerson = onOpenPerson,
                onEventClick = { eventId ->
                    expandedEventId = if (expandedEventId == eventId) null else eventId
                },
            )
        }
    }
}
