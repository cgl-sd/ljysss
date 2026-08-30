package com.ljyss.ui.people

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.MingRepository
import com.ljyss.data.model.PeopleTab
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.Reign
import com.ljyss.domain.parentChildTypes
import com.ljyss.domain.orderedPeopleForCards
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.ljyss.ui.components.MingList
import com.ljyss.ui.relationship.EventRelationshipNetwork
import com.ljyss.ui.relationship.RelationView
import com.ljyss.ui.relationship.RelationViewRail
import com.ljyss.ui.relationship.RelationshipLedger
import com.ljyss.ui.relationship.RelationshipNetwork
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.timeline.ReignRail
import com.ljyss.ui.components.SourceNote
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion

@Composable
internal fun PeopleScreen(
    repository: MingRepository,
    contentPadding: PaddingValues,
    focusPerson: String? = null,
    onFocusConsumed: () -> Unit = {},
) {
    var selectedTab by rememberSaveable { mutableStateOf(PeopleTab.DYNASTY) }
    var selectedCategory by rememberSaveable { mutableStateOf(PersonCategory.EMPERORS) }
    var selectedReignTitle by rememberSaveable { mutableStateOf("洪武") }
    // 默认筛选洪武；再次点击当前朝代即可取消筛选、显示当前分类的全部人物。
    var selectedPeopleReign by rememberSaveable { mutableStateOf<String?>("洪武") }
    var query by rememberSaveable { mutableStateOf("") }
    var selectedPersonName by rememberSaveable { mutableStateOf<String?>(null) }
    var selectedArchiveEventId by rememberSaveable { mutableStateOf<String?>(null) }
    var personStack by rememberSaveable { mutableStateOf(listOf<String>()) }
    var returnListIndex by rememberSaveable { mutableStateOf<Int?>(null) }
    var returnListOffset by rememberSaveable { mutableStateOf(0) }
    var relationView by rememberSaveable { mutableStateOf(RelationView.PERSON) }
    val reigns = remember(repository) { repository.reigns() }
    val relations = remember(repository) { repository.personRelations() }
    val allPeople = remember(repository) { repository.allPeople() }
    // 两个入口必须共用人物卡排序；搜索与切类目仅做线性过滤。
    val sortedPeople = remember(repository) {
        orderedPeopleForCards(allPeople)
    }
    val allEvents = remember(reigns) { reigns.flatMap { it.events } }
    val selectedPerson = allPeople.firstOrNull { it.name == selectedPersonName }
    val selectedArchiveEvent = allEvents.firstOrNull { it.id == selectedArchiveEventId }
    val peopleListState = rememberLazyListState()
    var profileDetail by remember(selectedPerson?.id) { mutableStateOf(selectedPerson) }
    LaunchedEffect(selectedPerson?.id) {
        val person = selectedPerson
        if (person != null && profileDetail?.sections.isNullOrEmpty()) {
            val full = withContext(Dispatchers.IO) { repository.personDetail(person.id) }
            if (full != null && full.sections.isNotEmpty()) profileDetail = full
        }
    }
    val childrenByPerson = remember(relations) {
        relations
            .filter { it.type in parentChildTypes() }
            .groupBy { it.fromName }
            .mapValues { entry -> entry.value.map { it.toName } }
    }
    val people = remember(sortedPeople, selectedCategory, selectedPeopleReign, query) {
        val keyword = query.trim()
        sortedPeople.filter { person ->
            person.category == selectedCategory &&
                (selectedPeopleReign?.let { person.reign.contains(it) } ?: true) &&
                (keyword.isBlank() || person.name.contains(keyword) || person.title.contains(keyword) || person.reign.contains(keyword))
        }
    }

    fun returnFromProfile() {
        selectedPersonName = null
        personStack = emptyList()
    }

    fun openArchiveEvent(event: com.ljyss.data.model.HistoricalEvent) {
        returnListIndex = peopleListState.firstVisibleItemIndex
        returnListOffset = peopleListState.firstVisibleItemScrollOffset
        selectedArchiveEventId = event.id
    }

    fun openProfileFromBrowse(name: String) {
        returnListIndex = peopleListState.firstVisibleItemIndex
        returnListOffset = peopleListState.firstVisibleItemScrollOffset
        selectedPersonName = name
        personStack = emptyList()
    }

    LaunchedEffect(selectedPersonName) {
        val index = returnListIndex
        if (selectedPersonName == null && index != null) {
            peopleListState.scrollToItem(index, returnListOffset)
            returnListIndex = null
        }
    }

    // 人物详情内跳转另一人物时保留来路，返回键与页内返回逐层回退，最后才退出详情。
    fun openRelatedPerson(targetName: String) {
        val current = selectedPersonName
        if (current != null && current != targetName && allPeople.any { it.name == targetName }) {
            personStack = personStack + current
            selectedPersonName = targetName
        }
    }

    fun closeProfileStep() {
        val previous = personStack.lastOrNull()
        if (previous != null) {
            personStack = personStack.dropLast(1)
            selectedPersonName = previous
        } else {
            returnFromProfile()
        }
    }

    // 岁月事件里的参与人物点击后跳转至对应人物详情。
    LaunchedEffect(focusPerson) {
        if (focusPerson != null) {
            allPeople.firstOrNull { it.name == focusPerson }?.let { person ->
                selectedTab = PeopleTab.PEOPLE
                selectedCategory = person.category
                query = person.name
                selectedPersonName = person.name
                personStack = emptyList()
            }
            onFocusConsumed()
        }
    }

    // 人物履历打开后，系统返回键与悬浮返回键保持同一行为，并保留进入详情前的页面状态。
    BackHandler(enabled = selectedPersonName != null || selectedArchiveEventId != null) {
        if (selectedPersonName != null) closeProfileStep() else selectedArchiveEventId = null
    }

    Box(modifier = Modifier.fillMaxSize()) {
        MingList(contentPadding, state = peopleListState) {
            if (selectedPerson != null) {
                item {
                    PersonProfile(
                        person = profileDetail ?: selectedPerson,
                        relations = relations,
                        onOpenPerson = ::openRelatedPerson,
                    )
                }
            } else if (selectedArchiveEvent != null) {
                item {
                    ArchiveEventProfile(
                        event = selectedArchiveEvent,
                        onOpenPerson = { name ->
                            if (allPeople.any { it.name == name }) openProfileFromBrowse(name)
                        },
                    )
                }
            } else {
                item { MingMasthead() }
                item { OrnamentalTitle("人物") }
                item {
                    PeopleTabRail(
                        selected = selectedTab,
                        onSelected = {
                            selectedTab = it
                            selectedPersonName = null
                            selectedArchiveEventId = null
                            personStack = emptyList()
                        },
                    )
                }
                when (selectedTab) {
            PeopleTab.DYNASTY -> {
                val selectedReign = reigns.firstOrNull { it.title == selectedReignTitle } ?: reigns.first()
                item {
                    ReignRail(reigns, selectedReign.title) {
                        selectedReignTitle = it
                            selectedArchiveEventId = null
                    }
                }
                item {
                    DynastyArchive(
                        reign = selectedReign,
                        people = allPeople.filter { it.reign.contains(selectedReign.title) },
                        onPersonSelected = { person ->
                            openProfileFromBrowse(person.name)
                        },
                        onOpenPerson = { name ->
                            if (allPeople.any { it.name == name }) {
                                openProfileFromBrowse(name)
                            }
                        },
                        onEventSelected = ::openArchiveEvent,
                    )
                }
            }
            PeopleTab.PEOPLE -> {
                item {
                    CategoryRail(
                        selectedCategory = selectedCategory,
                        onSelected = { selectedCategory = it },
                    )
                }
                item {
                    OutlinedTextField(
                        value = query,
                        onValueChange = { query = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = CutCornerShape(7.dp),
                        placeholder = {
                            Text("搜索姓名、官职或年号", color = Brass.copy(alpha = 0.72f), fontFamily = FontFamily.Serif, fontSize = 18.sp)
                        },
                        leadingIcon = {
                            Icon(Icons.Outlined.Search, contentDescription = null, tint = Brass)
                        },
                    )
                }
                item {
                    PersonChronologyRail(
                        reigns = reigns,
                        selectedReign = selectedPeopleReign,
                        onSelected = { reign ->
                            selectedPeopleReign = if (selectedPeopleReign == reign) null else reign
                        },
                    )
                }
                if (people.isEmpty()) {
                    item { SourceNote("没有相符人物。可搜索姓名、身份或年号。") }
                } else {
                    items(people, key = { it.name }) { person ->
                        PersonCard(
                            person = person,
                            children = childrenByPerson[person.name].orEmpty(),
                            expanded = false,
                            onClick = {
                                openProfileFromBrowse(person.name)
                            },
                        )
                    }
                }
            }
            PeopleTab.RELATIONSHIPS -> {
                item {
                    RelationViewRail(
                        selected = relationView,
                        onSelected = { relationView = it },
                    )
                }
                if (relationView == RelationView.PERSON) {
                    item { RelationshipNetwork(repository.personRelations()) }
                    item { RelationshipLedger(repository.personRelations()) }
                } else {
                    item { EventRelationshipNetwork(allEvents) }
                }
            }
                }
            }
        }
    }
}

@Composable
private fun PersonChronologyRail(
    reigns: List<Reign>,
    selectedReign: String?,
    onSelected: (String) -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = PaperLight.copy(alpha = 0.62f),
        shape = CutCornerShape(6.dp),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.8f)),
    ) {
        Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            Text("人物年表", color = Ink, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 5.dp),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                items(reigns, key = { it.title }) { reign ->
                    val firstYear = reign.yearRange.substringBefore("—")
                    val selected = reign.title == selectedReign
                    Row(
                        modifier = Modifier
                            .clip(CutCornerShape(4.dp))
                            .clickable { onSelected(reign.title) }
                            .padding(horizontal = 5.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Surface(
                            modifier = Modifier.size(if (selected) 8.dp else 6.dp),
                            shape = RoundedCornerShape(50),
                            color = if (selected) Vermilion else Brass,
                        ) {}
                        Column {
                            Text(
                                reign.title,
                                color = if (selected) Vermilion else Ink,
                                fontFamily = FontFamily.Serif,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(firstYear, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 9.sp)
                        }
                        HorizontalDivider(modifier = Modifier.width(14.dp), color = Brass, thickness = 1.dp)
                    }
                }
            }
        }
    }
}

@Composable
private fun CategoryRail(selectedCategory: PersonCategory, onSelected: (PersonCategory) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        PersonCategory.entries.forEach { category ->
            val selected = category == selectedCategory
            Surface(
                modifier = Modifier
                    .weight(1f)
                    .clip(CutCornerShape(6.dp))
                    .clickable { onSelected(category) },
                color = if (selected) Vermilion else PaperLight,
                shape = CutCornerShape(6.dp),
                border = BorderStroke(1.dp, if (selected) Vermilion else LineGold),
            ) {
                Text(
                    text = category.label,
                    modifier = Modifier.padding(horizontal = 2.dp, vertical = 8.dp),
                    color = if (selected) PaperLight else Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    textAlign = TextAlign.Center,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

@Composable
private fun PeopleTabRail(selected: PeopleTab, onSelected: (PeopleTab) -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = PaperLight.copy(alpha = 0.88f),
        shape = CutCornerShape(8.dp),
        border = BorderStroke(1.dp, LineGold),
    ) {
        Row(modifier = Modifier.padding(4.dp)) {
            PeopleTab.entries.forEach { tab ->
                val active = selected == tab
                Text(
                    text = tab.label,
                    modifier = Modifier
                        .weight(1f)
                        .clip(CutCornerShape(5.dp))
                        .clickable { onSelected(tab) }
                        .background(if (active) Vermilion else Color.Transparent)
                        .padding(vertical = 10.dp),
                    color = if (active) PaperLight else Ink,
                    textAlign = TextAlign.Center,
                    fontFamily = FontFamily.Serif,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}
