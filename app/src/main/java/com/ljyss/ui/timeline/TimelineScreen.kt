package com.ljyss.ui.timeline

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.unit.sp
import com.ljyss.data.MingRepository
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.domain.startYear
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.people.DynastyArchive
import com.ljyss.ui.people.ArchiveEventCard
import com.ljyss.ui.people.ArchiveEventProfile
import com.ljyss.ui.people.ArchiveSectionHeading
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
    val relations = remember(repository) { repository.personRelations() }
    var selectedTitle by rememberSaveable { mutableStateOf(reigns.first().title) }
    var selectedYear by rememberSaveable { mutableIntStateOf(reigns.first().startYear()) }
    var selectedArchiveEventId by rememberSaveable { mutableStateOf<String?>(null) }
    val archiveListState = rememberLazyListState()
    val eventDetailListState = rememberLazyListState()
    val selectedReign = reigns.first { it.title == selectedTitle }
    val archiveEvents = remember(selectedReign) {
        selectedReign.events.sortedWith(compareBy<HistoricalEvent>({ it.year ?: Int.MAX_VALUE }, { it.month }, { it.title }))
    }
    fun eventKey(event: HistoricalEvent): String = event.id.ifBlank {
        "${event.year ?: 0}:${event.title}"
    }
    val selectedArchiveEvent = reigns.flatMap { it.events }.firstOrNull { eventKey(it) == selectedArchiveEventId }
    // 每次打开新事件都从列表首项开始；从人物详情返回同一事件时保持原滚动位置。
    var lastOpenedEventKey by rememberSaveable { mutableStateOf<String?>(null) }
    LaunchedEffect(selectedArchiveEventId) {
        val key = selectedArchiveEventId
        if (key != null && key != lastOpenedEventKey) {
            eventDetailListState.scrollToItem(0)
            lastOpenedEventKey = key
        }
    }
    LaunchedEffect(searchDestination) {
        val destination = searchDestination ?: return@LaunchedEffect
        destination.reignTitle?.takeIf { title -> reigns.any { it.title == title } }?.let { title ->
            selectedTitle = title
            selectedYear = destination.year ?: reigns.first { it.title == title }.startYear()
            selectedArchiveEventId = destination.eventId
        }
        onSearchDestinationConsumed()
    }
    BackHandler(enabled = selectedArchiveEvent != null) {
        selectedArchiveEventId = null
    }

    if (selectedArchiveEvent != null) {
        MingList(contentPadding, state = eventDetailListState) {
            item { ArchiveEventProfile(selectedArchiveEvent, relations, onOpenPerson) }
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
                    showEvents = false,
                    onEventSelected = { event ->
                        // 正式库事件都有稳定 id；兜底键用于兼容编辑中的旧条目，
                        // 让任何可见卡片都不会因为空 id 而失去详情入口。
                        selectedArchiveEventId = eventKey(event)
                    },
                )
            }
            item { ArchiveSectionHeading("本朝大事") }
            if (archiveEvents.isEmpty()) {
                item {
                    androidx.compose.material3.Text(
                        "该朝事件正在按年份与史料卷次整理。",
                        color = com.ljyss.ui.theme.InkSoft,
                        fontFamily = androidx.compose.ui.text.font.FontFamily.Serif,
                        fontSize = 14.sp,
                    )
                }
            } else {
                items(archiveEvents, key = { eventKey(it) }) { event ->
                    ArchiveEventCard(
                        event = event,
                        onClick = {
                            selectedArchiveEventId = eventKey(event)
                        },
                        onOpenPerson = onOpenPerson,
                    )
                }
            }
    }
}
