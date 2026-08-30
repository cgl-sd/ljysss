package com.ljyss.ui.timeline

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
import com.ljyss.ui.people.DynastyArchive
import com.ljyss.ui.search.SearchDestination

@Composable
internal fun TimelineScreen(
    repository: MingRepository,
    contentPadding: PaddingValues,
    onOpenPerson: (String) -> Unit = {},
    searchDestination: SearchDestination? = null,
    onSearchDestinationConsumed: () -> Unit = {},
    onSearch: () -> Unit = {},
) {
    val reigns = remember(repository) { repository.reigns() }
    val allPeople = remember(repository) { repository.allPeople() }
    var selectedTitle by rememberSaveable { mutableStateOf(reigns.first().title) }
    var selectedYear by rememberSaveable { mutableIntStateOf(reigns.first().startYear()) }
    var expandedEventId by rememberSaveable { mutableStateOf<String?>(null) }
    val selectedReign = reigns.first { it.title == selectedTitle }
    LaunchedEffect(searchDestination) {
        val destination = searchDestination ?: return@LaunchedEffect
        destination.reignTitle?.takeIf { title -> reigns.any { it.title == title } }?.let { title ->
            selectedTitle = title
            selectedYear = destination.year ?: reigns.first { it.title == title }.startYear()
            expandedEventId = destination.eventId
        }
        onSearchDestinationConsumed()
    }

    MingList(contentPadding) {
        item { MingMasthead(onSearch) }
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
        item {
            DynastyArchive(
                reign = selectedReign,
                people = allPeople.filter { it.reign.contains(selectedReign.title) },
                onPersonSelected = { person -> onOpenPerson(person.name) },
                onOpenPerson = onOpenPerson,
                onEventSelected = { event ->
                    selectedYear = event.year ?: selectedReign.startYear()
                    expandedEventId = event.id
                },
            )
        }
    }
}
