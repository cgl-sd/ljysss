package com.ljyss.ui.search

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.activity.compose.BackHandler
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.MingRepository
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.components.mingScrollbar

/** 搜索结果的去向。sectionIndex 与底部四页保持同一顺序。 */
data class SearchDestination(
    val sectionIndex: Int,
    val personName: String? = null,
    val reignTitle: String? = null,
    val year: Int? = null,
    val eventId: String? = null,
    val worldSection: String? = null,
    val worldCategory: String? = null,
    val guideId: String? = null,
)

private data class SearchResult(
    val id: String,
    val kind: String,
    val title: String,
    val excerpt: String,
    val haystack: String,
    val destination: SearchDestination,
)

private enum class SearchFilter(val label: String) {
    ALL("全部"), PEOPLE("人物"), TIMELINE("岁月"), WORLD("天下"), GUIDE("手册"),
}

/** 全屏检索路由，替代遮住原页的对话框；返回时无缝回到此前阅读位置。 */
@Composable
fun GlobalSearchScreen(
    repository: MingRepository,
    onDismiss: () -> Unit,
    onNavigate: (SearchDestination) -> Unit,
) {
    var query by remember { mutableStateOf("") }
    var filter by remember { mutableStateOf(SearchFilter.ALL) }
    val searchFocus = remember { FocusRequester() }
    val results = remember(repository, query, filter) {
        searchCatalog(repository, query).filter { result -> filter.matches(result) }
    }
    val resultListState = rememberLazyListState()
    BackHandler(onBack = onDismiss)
    LaunchedEffect(Unit) { searchFocus.requestFocus() }
    Surface(modifier = Modifier.fillMaxSize(), color = PaperLight) {
        Column(
            modifier = Modifier.padding(start = 20.dp, top = 48.dp, end = 20.dp, bottom = 22.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Outlined.ArrowBack, contentDescription = "返回", tint = Ink)
                }
                Text("检索", color = Ink, fontFamily = FontFamily.Serif, fontSize = 28.sp, fontWeight = FontWeight.Bold)
            }
            SearchField(query = query, onQueryChange = { query = it }, modifier = Modifier.focusRequester(searchFocus))
            SearchFilterRail(filter) { filter = it }
            when {
                query.isBlank() -> Text(
                    "输入关键词，即可检索人物、岁月、天下与手册资料。",
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                )
                results.isEmpty() -> SearchEmptyState()
                else -> LazyColumn(
                    modifier = Modifier.weight(1f).mingScrollbar(resultListState),
                    state = resultListState,
                    verticalArrangement = Arrangement.spacedBy(1.dp),
                ) {
                    item {
                        Text("检得 ${results.size} 条", modifier = Modifier.padding(bottom = 8.dp), color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                    }
                    items(results, key = { it.id }) { result ->
                        SearchResultCard(result) { onNavigate(result.destination) }
                    }
                }
            }
        }
    }
}

@Composable
private fun SearchFilterRail(selected: SearchFilter, onSelected: (SearchFilter) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        SearchFilter.entries.forEach { filter ->
            val active = filter == selected
            Text(
                filter.label,
                modifier = Modifier
                    .clip(CutCornerShape(5.dp))
                    .clickable { onSelected(filter) }
                    .padding(horizontal = 13.dp, vertical = 8.dp),
                color = if (active) Vermilion else Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 17.sp,
                fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
            )
        }
    }
}

@Composable
private fun SearchField(query: String, onQueryChange: (String) -> Unit, modifier: Modifier = Modifier) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = PaperShade.copy(alpha = 0.52f),
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.82f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.Search, contentDescription = null, tint = Vermilion, modifier = Modifier.padding(end = 9.dp))
            Box(modifier = Modifier.weight(1f).padding(vertical = 10.dp)) {
                if (query.isBlank()) {
                    Text("姓名、年号、官职、事件、机构、典章或手册", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
                }
                BasicTextField(
                    value = query,
                    onValueChange = onQueryChange,
                    modifier = modifier.fillMaxWidth(),
                    singleLine = true,
                    textStyle = TextStyle(color = Ink, fontFamily = FontFamily.Serif, fontSize = 16.sp),
                )
            }
        }
    }
}

@Composable
private fun SearchEmptyState() {
    Text("未寻得相符条目。可尝试姓名、年号、官职、机构或手册主题。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
}

@Composable
private fun SearchResultCard(result: SearchResult, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().clip(CutCornerShape(2.dp)).clickable(onClick = onClick),
        shape = CutCornerShape(2.dp),
        color = PaperLight,
        border = BorderStroke(0.75.dp, LineGold.copy(alpha = 0.65f)),
    ) {
        Row(modifier = Modifier.padding(horizontal = 11.dp, vertical = 10.dp), verticalAlignment = Alignment.Top) {
            Surface(shape = CutCornerShape(3.dp), color = Vermilion) {
                Text(result.kind, modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp), color = PaperLight, fontFamily = FontFamily.Serif, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
            Column(modifier = Modifier.padding(start = 10.dp).weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(result.title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                Text(result.excerpt, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 13.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

private fun SearchFilter.matches(result: SearchResult): Boolean = when (this) {
    SearchFilter.ALL -> true
    SearchFilter.PEOPLE -> result.kind == "人物"
    SearchFilter.TIMELINE -> result.kind == "年号" || result.kind == "大事"
    SearchFilter.WORLD -> result.kind == "机构" || result.kind == "典章"
    SearchFilter.GUIDE -> result.kind == "手册"
}

private fun searchCatalog(repository: MingRepository, rawQuery: String): List<SearchResult> {
    val query = rawQuery.trim().lowercase()
    if (query.isBlank()) return emptyList()
    fun text(value: String) = value.replace(Regex("\\s+"), " ").trim()
    fun eventText(reign: String, event: HistoricalEvent) = listOf(reign, event.year, event.month, event.title, event.description, event.detail, event.place, event.participants.joinToString("、"), event.consequence).joinToString(" ")
    val results = buildList {
        repository.allPeople().forEach { person ->
            val searchable = listOf(person.displayName, person.name, person.title, person.reign, person.years, person.note, person.biography, person.courtesyName)
                .plus(person.sections.map { it.title + " " + it.content })
                .joinToString(" ")
            add(SearchResult("person:${person.id}", "人物", person.displayName, text("${person.title}｜${person.reign}｜${person.note}"), searchable, SearchDestination(1, personName = person.name)))
        }
        repository.reigns().forEach { reign ->
            add(SearchResult("reign:${reign.title}", "年号", reign.title, text("${reign.yearRange}｜${reign.summary}"), "${reign.title} ${reign.yearRange} ${reign.summary}", SearchDestination(0, reignTitle = reign.title)))
            reign.events.forEach { event ->
                add(SearchResult("event:${event.id}", "大事", event.title, text("${reign.title}${event.year ?: ""}年｜${event.description}"), eventText(reign.title, event), SearchDestination(0, reignTitle = reign.title, year = event.year, eventId = event.id)))
            }
        }
        repository.institutions().forEach { institution ->
            val searchable = listOf(institution.name, institution.category, institution.activeReigns, institution.function)
                .plus(institution.promotionTracks.flatMap { track -> listOf(track.title) + track.steps })
                .plus(institution.reforms.flatMap { listOf(it.year, it.title, it.description) })
                .joinToString(" ")
            add(SearchResult("institution:${institution.id}", "机构", institution.name, text("${institution.category}｜${institution.function}"), searchable, SearchDestination(2, worldSection = "机构", worldCategory = institution.category)))
        }
        repository.specialItems().forEach { item ->
            add(SearchResult("special:${item.id}", "典章", item.name, text("${item.category}｜${item.era}｜${item.description}"), "${item.name} ${item.category} ${item.era} ${item.description}", SearchDestination(2, worldSection = "典章", worldCategory = item.category)))
        }
        repository.travelGuides().forEach { guide ->
            val searchable = listOf(guide.title, guide.category, guide.subtitle, guide.description)
                .plus(guide.sections.map { it.title + " " + it.content })
                .joinToString(" ")
            add(SearchResult("guide:${guide.id}", "手册", guide.title, text("${guide.category}｜${guide.description}"), searchable, SearchDestination(3, guideId = guide.id)))
        }
    }
    return results.filter { it.haystack.lowercase().contains(query) }.take(80)
}
