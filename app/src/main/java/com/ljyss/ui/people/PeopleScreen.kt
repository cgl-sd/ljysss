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
import androidx.compose.material3.HorizontalDivider
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
import com.ljyss.ui.relationship.RelationshipLedger
import com.ljyss.ui.relationship.RelationshipNetwork
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.timeline.ReignRail
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
    focusPersonId: String? = null,
    onFocusConsumed: () -> Unit = {},
    onProfileExit: () -> Unit = {},
    onSearch: () -> Unit = {},
) {
    var selectedTab by rememberSaveable { mutableStateOf(PeopleTab.PEOPLE) }
    var selectedCategory by rememberSaveable { mutableStateOf(PersonCategory.EMPERORS) }
    // 默认筛选洪武；再次点击当前朝代即可取消筛选、显示当前分类的全部人物。
    var selectedPeopleReign by rememberSaveable { mutableStateOf<String?>("洪武") }
    var selectedPersonName by rememberSaveable { mutableStateOf<String?>(null) }
    // 人物页中的事件详情在本页栈内打开：返回时稳定回到原人物，而不依赖切换底部导航。
    var selectedRelatedEventId by rememberSaveable { mutableStateOf<String?>(null) }
    var personStack by rememberSaveable { mutableStateOf(listOf<String>()) }
    var returnListIndex by rememberSaveable { mutableStateOf<Int?>(null) }
    var returnListOffset by rememberSaveable { mutableStateOf(0) }
    val reigns = remember(repository) { repository.reigns() }
    val relations = remember(repository) { repository.personRelations() }
    val allPeople = remember(repository) { repository.allPeople() }
    val allEvents = remember(reigns) { reigns.flatMap { it.events } }
    // A root destination is rendered immediately; the local selection is filled by the effect
    // below for subsequent profile-to-profile navigation and back-stack handling.
    val focusedPerson = focusPersonId?.let { id -> allPeople.firstOrNull { it.id == id } }
    val selectedPerson = focusedPerson ?: allPeople.firstOrNull { it.name == selectedPersonName }
    val selectedRelatedEvent = allEvents.firstOrNull { it.id == selectedRelatedEventId }
    val peopleListState = rememberLazyListState()
    val eventDetailListState = rememberLazyListState()
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
    val people = remember(allPeople, selectedCategory, selectedPeopleReign) {
        val filtered = allPeople.filter { person ->
            person.category == selectedCategory &&
                (selectedPeopleReign?.let { person.reign.contains(it) } ?: true)
        }
        orderedPeopleForCards(filtered, selectedPeopleReign)
    }

    fun returnFromProfile() {
        selectedRelatedEventId = null
        selectedPersonName = null
        personStack = emptyList()
        onProfileExit()
    }

    fun openProfileFromBrowse(name: String) {
        selectedRelatedEventId = null
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

    fun openRelatedEvent(eventId: String) {
        if (allEvents.any { it.id == eventId }) {
            selectedRelatedEventId = eventId
        }
    }

    fun openPersonFromEvent(targetName: String) {
        selectedRelatedEventId = null
        if (selectedPersonName == null) openProfileFromBrowse(targetName) else openRelatedPerson(targetName)
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
    LaunchedEffect(focusPersonId) {
        if (focusPersonId != null) {
            allPeople.firstOrNull { it.id == focusPersonId }?.let { person ->
                selectedTab = PeopleTab.PEOPLE
                selectedCategory = person.category
                selectedPersonName = person.name
                personStack = emptyList()
            }
            onFocusConsumed()
        }
    }

    // 人物履历打开后，系统返回键与悬浮返回键保持同一行为，并保留进入详情前的页面状态。
    BackHandler(enabled = selectedRelatedEvent != null) {
        selectedRelatedEventId = null
    }
    BackHandler(enabled = selectedPersonName != null && selectedRelatedEvent == null) {
        closeProfileStep()
    }

    Box(modifier = Modifier.fillMaxSize()) {
        if (selectedRelatedEvent != null) {
            // 事件使用独立滚动状态；关闭后不会覆盖人物详情或人物列表原有的位置。
            MingList(contentPadding, state = eventDetailListState) {
                item {
                    ArchiveEventProfile(selectedRelatedEvent, ::openPersonFromEvent)
                }
            }
        } else {
            MingList(contentPadding, state = peopleListState) {
                if (selectedPerson != null) {
                    item {
                        PersonProfile(
                            person = profileDetail ?: selectedPerson,
                            relations = relations,
                            onOpenPerson = ::openRelatedPerson,
                            onOpenEvent = ::openRelatedEvent,
                        )
                    }
                } else {
                    item { MingMasthead(onSearch) }
                    item { OrnamentalTitle("人物") }
                    item {
                        PeopleTabRail(
                            selected = selectedTab,
                            onSelected = {
                                selectedTab = it
                                selectedPersonName = null
                                personStack = emptyList()
                            },
                        )
                    }
                    when (selectedTab) {
                        PeopleTab.PEOPLE -> {
                            item {
                                CategoryRail(
                                    selectedCategory = selectedCategory,
                                    onSelected = { selectedCategory = it },
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
                                item {
                                    Text("当前筛选下暂无人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
                                }
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
                                RelationshipNetwork(
                                    relations,
                                    allEvents,
                                    onOpenPerson = { name ->
                                        if (selectedPersonName == null) openProfileFromBrowse(name) else openRelatedPerson(name)
                                    },
                                )
                            }
                            item { RelationshipLedger(relations) }
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
