package com.ljyss.ui.timeline

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.activity.compose.BackHandler
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
import com.ljyss.ui.people.ArchiveEventProfile
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
    var selectedArchiveEventId by rememberSaveable { mutableStateOf<String?>(null) }
    val archiveListState = rememberLazyListState()
    val eventDetailListState = rememberLazyListState()
    val selectedReign = reigns.first { it.title == selectedTitle }
    val selectedArchiveEvent = reigns.flatMap { it.events }.firstOrNull { it.id == selectedArchiveEventId }
    LaunchedEffect(searchDestination) {
        val destination = searchDestination ?: return@LaunchedEffect
        destination.reignTitle?.takeIf { title -> reigns.any { it.title == title } }?.let { title ->
            selectedTitle = title
            selectedYear = destination.year ?: reigns.first { it.title == title }.startYear()
            selectedArchiveEventId = destination.eventId
        }
        onSearchDestinationConsumed()
    }
    BackHandler(enabled = selectedArchiveEvent != null) { selectedArchiveEventId = null }

    if (selectedArchiveEvent != null) {
        MingList(contentPadding, state = eventDetailListState) {
            item { ArchiveEventProfile(selectedArchiveEvent, onOpenPerson) }
        }
    } else MingList(contentPadding, state = archiveListState) {
            item { MingMasthead(onSearch) }
            item { OrnamentalTitle("岁月") }
            item {
                ReignRail(reigns, selectedTitle) {
                    selectedTitle = it
                    selectedYear = reigns.first { reign -> reign.title == it }.startYear()
                    selectedArchiveEventId = null
                }
            }
            item {
                ReignYearRail(
                    reign = selectedReign,
                    selectedYear = selectedYear,
                    onSelected = { selectedYear = it },
                )
            }
            item {
                DynastyArchive(
                    reign = selectedReign,
                    people = allPeople.filter { it.reign.contains(selectedReign.title) },
                    onPersonSelected = { person -> onOpenPerson(person.name) },
                    onOpenPerson = onOpenPerson,
                    onEventSelected = { event -> selectedArchiveEventId = event.id },
                )
            }
    }
}
