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
import com.ljyss.domain.bestMatch
import com.ljyss.domain.normalizeSearchText
import com.ljyss.domain.rankByFirstMatch
import com.ljyss.domain.toPinyin
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.components.mingScrollbar
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

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
    val resultListState = rememberLazyListState()
    var index by remember { mutableStateOf(emptyList<IndexedResult>()) }
    var results by remember { mutableStateOf(emptyList<SearchResult>()) }
    LaunchedEffect(repository) {
        index = withContext(Dispatchers.Default) { buildSearchIndex(repository) }
    }
    LaunchedEffect(query, filter, index) {
        delay(150)
        results = withContext(Dispatchers.Default) {
            val normalized = normalizeSearchText(query)
            val ranked = if (normalized.isBlank()) emptyList()
            else rankByFirstMatch(
                index.map { indexed -> indexed.result to bestMatch(indexed.haystack, normalized, indexed.pinyin) },
            )
            ranked.filter { filter.matches(it) }.take(80)
        }
    }
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
                query.isBlank() || index.isEmpty() -> Text(
                    "输入中文或拼音，即可检索人物、岁月、天下与手册资料。",
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
        shape = RoundedCornerShape(50),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.82f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.Search, contentDescription = null, tint = Vermilion, modifier = Modifier.padding(end = 9.dp))
            Box(modifier = Modifier.weight(1f).padding(vertical = 10.dp)) {
                if (query.isBlank()) {
                    Text("姓名、年号、官职、事件、机构……", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
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
    Text("未寻得相符条目。可尝试姓名、年号、官职、机构或手册主题（支持拼音）。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
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

/** 检索索引项：haystack 已归一化，pinyin 一次性预计算，避免逐键重复转换全库文本。 */
private data class IndexedResult(
    val result: SearchResult,
    val haystack: String,
    val pinyin: String,
)

private fun buildSearchIndex(repository: MingRepository): List<IndexedResult> {
    fun text(value: String) = value.replace(Regex("\\s+"), " ").trim()
    fun eventText(reign: String, event: HistoricalEvent) = listOf(reign, event.year, event.month, event.title, event.description, event.detail, event.place, event.participants.joinToString("、"), event.consequence).joinToString(" ")
    fun indexed(result: SearchResult, searchable: String): IndexedResult {
        val haystack = normalizeSearchText(searchable)
        return IndexedResult(result, haystack, toPinyin(haystack))
    }
    return buildList {
        repository.allPeople().forEach { person ->
            val searchable = listOf(person.displayName, person.name, person.title, person.reign, person.years, person.note, person.biography, person.courtesyName)
                .plus(person.sections.map { it.title + " " + it.content })
                .joinToString(" ")
            add(indexed(SearchResult("person:${person.id}", "人物", person.displayName, text("${person.title}｜${person.reign}｜${person.note}"), SearchDestination(1, personName = person.name)), searchable))
        }
        repository.reigns().forEach { reign ->
            add(indexed(SearchResult("reign:${reign.title}", "年号", reign.title, text("${reign.yearRange}｜${reign.summary}"), SearchDestination(0, reignTitle = reign.title)), "${reign.title} ${reign.yearRange} ${reign.summary}"))
            reign.events.forEach { event ->
                add(indexed(SearchResult("event:${event.id}", "大事", event.title, text("${reign.title}${event.year ?: ""}年｜${event.description}"), SearchDestination(0, reignTitle = reign.title, year = event.year, eventId = event.id)), eventText(reign.title, event)))
            }
        }
        repository.institutions().forEach { institution ->
            val searchable = listOf(institution.name, institution.category, institution.activeReigns, institution.function)
                .plus(institution.promotionTracks.flatMap { track -> listOf(track.title) + track.steps })
                .plus(institution.reforms.flatMap { listOf(it.year, it.title, it.description) })
                .joinToString(" ")
            add(indexed(SearchResult("institution:${institution.id}", "机构", institution.name, text("${institution.category}｜${institution.function}"), SearchDestination(2, worldSection = "机构", worldCategory = institution.category)), searchable))
        }
        repository.specialItems().forEach { item ->
            add(indexed(SearchResult("special:${item.id}", "典章", item.name, text("${item.category}｜${item.era}｜${item.description}"), SearchDestination(2, worldSection = "典章", worldCategory = item.category)), "${item.name} ${item.category} ${item.era} ${item.description}"))
        }
        repository.travelGuides().forEach { guide ->
            val searchable = listOf(guide.title, guide.category, guide.subtitle, guide.description)
                .plus(guide.sections.map { it.title + " " + it.content })
                .joinToString(" ")
            add(indexed(SearchResult("guide:${guide.id}", "手册", guide.title, text("${guide.category}｜${guide.description}"), SearchDestination(3, guideId = guide.id)), searchable))
        }
    }
}
