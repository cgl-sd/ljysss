package com.ljyss.ui.search

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.ljyss.data.MingRepository
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion

/** 搜索结果的去向。sectionIndex 与底部四页保持同一顺序。 */
data class SearchDestination(
    val sectionIndex: Int,
    val personName: String? = null,
    val reignTitle: String? = null,
    val year: Int? = null,
    val eventId: String? = null,
    val worldSection: String? = null,
    val worldCategory: String? = null,
)

private data class SearchResult(
    val id: String,
    val kind: String,
    val title: String,
    val excerpt: String,
    val haystack: String,
    val destination: SearchDestination,
)

@Composable
fun GlobalSearchDialog(
    repository: MingRepository,
    onDismiss: () -> Unit,
    onNavigate: (SearchDestination) -> Unit,
) {
    var query by remember { mutableStateOf("") }
    val results = remember(repository, query) { searchCatalog(repository, query) }
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier.fillMaxWidth().fillMaxHeight(0.88f),
            shape = CutCornerShape(12.dp),
            color = PaperLight,
            border = BorderStroke(1.25.dp, LineGold),
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("全局搜索", modifier = Modifier.weight(1f), color = Ink, fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Outlined.Close, contentDescription = "关闭搜索", tint = InkSoft)
                    }
                }
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = CutCornerShape(7.dp),
                    leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null, tint = Vermilion) },
                    placeholder = { Text("搜索姓名、年号、官职、事件、机构、典章或全文", fontFamily = FontFamily.Serif) },
                )
                if (query.isBlank()) {
                    Text("输入关键词后，可跨人物、岁月、天下与我的资料检索。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
                } else if (results.isEmpty()) {
                    Text("未找到相符内容。可尝试姓名、年号、官职或机构名称。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
                } else {
                    Text("找到 ${results.size} 条结果", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp)
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(results, key = { it.id }) { result ->
                            SearchResultCard(result) {
                                onNavigate(result.destination)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SearchResultCard(result: SearchResult, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clip(CutCornerShape(7.dp)).clickable(onClick = onClick),
        shape = CutCornerShape(7.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperShade),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(result.kind, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text(result.title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Text(result.excerpt, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
    }
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
                .plus(institution.promotionPath)
                .plus(institution.reforms.flatMap { listOf(it.year, it.title, it.description) })
                .joinToString(" ")
            add(SearchResult("institution:${institution.id}", "机构", institution.name, text("${institution.category}｜${institution.function}"), searchable, SearchDestination(2, worldSection = "机构", worldCategory = institution.category)))
        }
        repository.specialItems().forEach { item ->
            add(SearchResult("special:${item.id}", "典章", item.name, text("${item.category}｜${item.era}｜${item.description}"), "${item.name} ${item.category} ${item.era} ${item.description}", SearchDestination(2, worldSection = "典章", worldCategory = item.category)))
        }
        profileSearchEntries.forEach { entry -> add(entry) }
    }
    return results.filter { it.haystack.lowercase().contains(query) }.take(80)
}

private val profileSearchEntries = listOf(
    SearchResult("profile:desk", "我的", "我的书案", "登录后可同步收藏、阅读进度与自建专题。", "我的 书案 收藏 阅读进度 自建专题", SearchDestination(3)),
    SearchResult("profile:database", "我的", "本地资料库", "人物、事件与分栏资料已随应用安装。", "我的 本地资料库 离线 人物 事件 分栏资料", SearchDestination(3)),
)
