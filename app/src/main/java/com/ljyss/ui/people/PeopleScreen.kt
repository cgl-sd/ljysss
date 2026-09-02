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
import androidx.compose.runtime.mutableIntStateOf
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
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PeopleTab
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.Reign
import com.ljyss.domain.parentChildTypes
import com.ljyss.domain.orderedPeopleForCards
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.relationship.RelationDetailScreen
import com.ljyss.ui.relationship.RelationPersonCard
import com.ljyss.ui.relationship.RelationRow
import com.ljyss.ui.timeline.ReignRail
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion
/** 人物页内的顶层页面：人物详情可叠在事件/关系详情之上，返回时逐层回退到跳转前的一页。 */
private enum class PeoplePage { LIST, EVENT, RELATION, PROFILE }

@Composable
internal fun PeopleScreen(
    repository: MingRepository,
    contentPadding: PaddingValues,
    focusPersonId: String? = null,
    onFocusConsumed: () -> Unit = {},
    onProfileExit: () -> Unit = {},
    onSearch: () -> Unit = {},
    onOpenMenu: () -> Unit = {},
) {
    var selectedTab by rememberSaveable { mutableStateOf(PeopleTab.PEOPLE) }
    var selectedCategory by rememberSaveable { mutableStateOf(PersonCategory.EMPERORS) }
    // 默认筛选洪武；再次点击当前朝代即可取消筛选、显示当前分类的全部人物。
    var selectedPeopleReign by rememberSaveable { mutableStateOf<String?>("洪武") }
    // 关系页年表筛选：与人物页年表同款，按人物主要纪年筛选关系分组。
    var selectedRelationReign by rememberSaveable { mutableStateOf<String?>(null) }
    var selectedPersonName by rememberSaveable { mutableStateOf<String?>(null) }
    // 人物页中的事件详情在本页栈内打开：返回时稳定回到原人物，而不依赖切换底部导航。
    var selectedRelatedEventId by rememberSaveable { mutableStateOf<String?>(null) }
    // 关系 tab 的关系详情同样在本页栈内打开，与事件详情互斥渲染。
    var selectedRelationKey by rememberSaveable { mutableStateOf<String?>(null) }
    // 页面栈：底 → 顶。人物详情可叠在事件/关系详情之上，返回时逐层回退。
    var pageStack by rememberSaveable { mutableStateOf(listOf(PeoplePage.LIST)) }
    var personStack by rememberSaveable { mutableStateOf(listOf<String>()) }
    var returnListIndex by rememberSaveable { mutableStateOf<Int?>(null) }
    var returnListOffset by rememberSaveable { mutableIntStateOf(0) }
    val reigns = remember(repository) { repository.reigns() }
    val relations = remember(repository) { repository.personRelations() }
    val allPeople = remember(repository) { repository.allPeople() }
    val allEvents = remember(reigns) { reigns.flatMap { it.events } }
    // 相关事件使用稳定 ID 索引；同时登记年份+标题回退键，兼容旧内容包中的空 ID。
    val eventByKey = remember(allEvents) {
        buildMap {
            allEvents.forEach { event ->
                if (event.id.isNotBlank()) put(event.id, event)
                putIfAbsent("${event.year}:${event.title}", event)
            }
        }
    }
    // A root destination is rendered immediately; the local selection is filled by the effect
    // below for subsequent profile-to-profile navigation and back-stack handling.
    val focusedPerson = focusPersonId?.let { id -> allPeople.firstOrNull { it.id == id } }
    val selectedPerson = focusedPerson ?: allPeople.firstOrNull { it.name == selectedPersonName }
    val selectedRelatedEvent = selectedRelatedEventId?.let { eventByKey[it] }
    val selectedRelation = selectedRelationKey?.let { key -> relations.firstOrNull { relationKey(it) == key } }
    // 跨页跳入人物时 focusPersonId 先于 LaunchedEffect 生效：顶层页面直接按
    // 目标人物渲染，避免先闪现人物 tab 列表再切到详情的过渡停顿。
    val topPage = if (focusedPerson != null) PeoplePage.PROFILE else pageStack.last()
    // 列表与各详情页各自维护滚动位置，互不覆盖；详情页返回时保留原位置。
    val peopleListState = rememberLazyListState()
    val profileListState = rememberLazyListState()
    val eventDetailListState = rememberLazyListState()
    val relationDetailListState = rememberLazyListState()
    LaunchedEffect(selectedRelatedEventId) {
        if (selectedRelatedEventId != null) eventDetailListState.scrollToItem(0)
    }
    var profileDetail by remember(selectedPerson?.id) { mutableStateOf(selectedPerson) }
    LaunchedEffect(selectedPerson?.id) {
        if (selectedPerson != null) profileListState.scrollToItem(0)
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
    val relationGroups = remember(relations, allPeople, reigns) {
        val peopleByName = allPeople.associateBy { it.name }
        val dynastyOrder = reigns.map { it.title }
        val rowsByPerson = mutableMapOf<String, MutableList<RelationRow>>()
        relations.forEach { relation ->
            rowsByPerson.getOrPut(relation.fromName) { mutableListOf() }
                .add(RelationRow(relation.toName, relation))
            rowsByPerson.getOrPut(relation.toName) { mutableListOf() }
                .add(RelationRow(relation.fromName, relation))
        }
        data class Group(val person: HistoricalPerson, val rows: List<RelationRow>)
        val groups = rowsByPerson.mapNotNull { (name, rows) ->
            peopleByName[name]?.let { person -> Group(person, rows) }
        }
        val byDynasty = groups.groupBy { group ->
            val primary = group.person.reign.substringBefore('、').trim()
            if (primary in dynastyOrder) primary else "其他"
        }
        dynastyOrder.mapNotNull { dynasty -> byDynasty[dynasty]?.let { dynasty to it } } +
            byDynasty.entries.filter { it.key !in dynastyOrder }.map { it.key to it.value }
    }

    fun returnFromProfile() {
        // 从人物详情逐层回退：先回事件/关系详情（保持其滚动位置），最后才回列表。
        selectedPersonName = null
        personStack = emptyList()
        pageStack = if (pageStack.size > 1) pageStack.dropLast(1) else listOf(PeoplePage.LIST)
        if (pageStack.last() == PeoplePage.LIST) {
            onProfileExit()
        }
    }

    fun openProfileFromBrowse(name: String) {
        // 从事件/关系详情跳人物时保留详情页：人物详情叠在其上，返回时原页仍在。
        returnListIndex = peopleListState.firstVisibleItemIndex
        returnListOffset = peopleListState.firstVisibleItemScrollOffset
        selectedPersonName = name
        personStack = emptyList()
        pageStack = pageStack + PeoplePage.PROFILE
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
        // 不再用 any 检查后静默丢弃点击；正式库中的 ID 由导入校验保证可解析。
        // 空 ID 的旧数据通过回退键仍可打开对应事件详情。
        if (eventId.isNotBlank()) {
            selectedRelatedEventId = eventId
            pageStack = pageStack + PeoplePage.EVENT
        }
    }

    fun openPersonFromEvent(targetName: String) {
        // 保留事件详情：人物详情叠在其上，返回时回到该事件。
        if (selectedPersonName == null) {
            returnListIndex = peopleListState.firstVisibleItemIndex
            returnListOffset = peopleListState.firstVisibleItemScrollOffset
            selectedPersonName = targetName
            personStack = emptyList()
            pageStack = pageStack + PeoplePage.PROFILE
        } else {
            openRelatedPerson(targetName)
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
    LaunchedEffect(focusPersonId) {
        if (focusPersonId != null) {
            allPeople.firstOrNull { it.id == focusPersonId }?.let { person ->
                selectedTab = PeopleTab.PEOPLE
                selectedCategory = person.category
                selectedPersonName = person.name
                personStack = emptyList()
                pageStack = listOf(PeoplePage.LIST, PeoplePage.PROFILE)
            }
            onFocusConsumed()
        }
    }

    BackHandler(enabled = topPage == PeoplePage.EVENT) {
        selectedRelatedEventId = null
        pageStack = pageStack.dropLast(1)
    }
    BackHandler(enabled = topPage == PeoplePage.RELATION) {
        selectedRelationKey = null
        pageStack = pageStack.dropLast(1)
    }
    BackHandler(enabled = topPage == PeoplePage.PROFILE) {
        closeProfileStep()
    }

    Box(modifier = Modifier.fillMaxSize()) {
        when (topPage) {
            PeoplePage.EVENT -> {
                // 事件使用独立滚动状态；关闭后不会覆盖人物详情或人物列表原有的位置。
                MingList(contentPadding, state = eventDetailListState) {
                    item {
                        ArchiveEventProfile(selectedRelatedEvent!!, relations, ::openPersonFromEvent)
                    }
                }
            }
            PeoplePage.RELATION -> {
                MingList(contentPadding, state = relationDetailListState) {
                    item {
                        RelationDetailScreen(
                            relation = selectedRelation!!,
                            relations = relations,
                            events = allEvents,
                            onOpenPerson = { name ->
                                if (selectedPersonName == null) openProfileFromBrowse(name) else openRelatedPerson(name)
                            },
                            onOpenEvent = { eventId -> openRelatedEvent(eventId) },
                        )
                    }
                }
            }
            PeoplePage.PROFILE -> {
                val profile = profileDetail ?: selectedPerson!!
                MingList(contentPadding, state = profileListState) {
                    item {
                        PersonProfile(
                            person = profile,
                            relations = relations,
                            onOpenPerson = ::openRelatedPerson,
                        )
                    }
                    if (profile.relatedEvents.isNotEmpty()) {
                        item {
                            PersonRelatedEventsPanel(
                                events = profile.relatedEvents,
                                onOpenEvent = ::openRelatedEvent,
                            )
                        }
                    }
                }
            }
            PeoplePage.LIST -> {
                MingList(contentPadding, state = peopleListState) {
                    item { MingMasthead(onSearch = onSearch, onOpenMenu = onOpenMenu) }
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
                                RelationChronologyRail(
                                    reigns = reigns,
                                    selectedReign = selectedRelationReign,
                                    onSelected = { reign ->
                                        selectedRelationReign = if (selectedRelationReign == reign) null else reign
                                    },
                                )
                            }
                            val shownGroups = selectedRelationReign?.let { selected ->
                                relationGroups.filter { it.first == selected }
                            } ?: relationGroups
                            if (shownGroups.isEmpty()) {
                                item {
                                    Text("当前筛选下暂无关系", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
                                }
                            }
                            shownGroups.flatMap { it.second }.forEach { group ->
                                item(key = "person-${group.person.id}") {
                                    RelationPersonCard(
                                        person = group.person,
                                        rows = group.rows,
                                        onOpenPerson = { openProfileFromBrowse(it) },
                                        onOpenRelation = { relation ->
                                            selectedRelationKey = relationKey(relation)
                                            pageStack = pageStack + PeoplePage.RELATION
                                        },
                                    )
                                }
                            }
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
private fun RelationChronologyRail(
    reigns: List<Reign>,
    selectedReign: String?,
    onSelected: (String) -> Unit,
) {
    // 与人物页年表同款：朝代点按时间顺序横排，选中高亮朱红，再次点击取消筛选。
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

/** 关系卡片的稳定 key：三人组合（甲乙名＋关系类型）。数据中该组合唯一。 */
private fun relationKey(relation: PersonRelation): String =
    "${relation.fromName}|${relation.type.label}|${relation.toName}"
