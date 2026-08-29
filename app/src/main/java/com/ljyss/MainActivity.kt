package com.ljyss

import android.os.Bundle
import android.util.Log
import androidx.activity.compose.BackHandler
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.DateRange
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.Layers
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.PersonOutline
import androidx.compose.material.icons.outlined.Public
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.MingRepository
import com.ljyss.data.RemoteMingRepository
import com.ljyss.data.SeedMingRepository
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.PeopleTab
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.RelationshipType
import com.ljyss.data.model.Institution
import com.ljyss.data.model.Reign
import com.ljyss.data.model.SpecialItem
import com.ljyss.domain.endYear
import com.ljyss.domain.lunarMonthOrder
import com.ljyss.domain.parseLifeBlocks
import com.ljyss.domain.parentChildTypes
import com.ljyss.domain.personBirthYear
import com.ljyss.domain.personChronologyRank
import com.ljyss.domain.readableParagraphs
import com.ljyss.domain.startYear
import com.ljyss.domain.yearLabel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.timeline.ReignRail
import com.ljyss.ui.timeline.TimelineScreen
import com.ljyss.ui.components.Seal
import com.ljyss.ui.components.SourceNote
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Indigo
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper
import com.ljyss.ui.theme.两京一十三省Theme
import kotlin.math.cos
import kotlin.math.sin

class MainActivity : ComponentActivity() {
    private var repository by mutableStateOf<MingRepository>(SeedMingRepository)

    @Volatile
    private var lastFetchFailed = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            两京一十三省Theme {
                TwoCapitalsApp(repository = repository)
            }
        }
        // 本地开发通过 `adb reverse tcp:8000 tcp:8000` 连接电脑上的内容服务；失败时保持离线资料。
        if (BuildConfig.DEBUG) {
            loadRemoteContent()
        }
    }

    override fun onResume() {
        super.onResume()
        // 启动时内容服务未连接的，回到前台自动重试，避免长期停留在离线种子资料。
        if (BuildConfig.DEBUG && lastFetchFailed) {
            loadRemoteContent()
        }
    }

    private fun loadRemoteContent() {
        Thread {
            lastFetchFailed = true
            runCatching { RemoteMingRepository.load("http://127.0.0.1:8000") }
                .onSuccess { remote ->
                    lastFetchFailed = false
                    runOnUiThread { repository = remote }
                }
                .onFailure { error -> Log.w("MingContent", "使用离线资料：内容服务未连接", error) }
        }.start()
    }
}

private data class AppSection(
    val label: String,
    val iconRes: Int? = null,
    val vectorIcon: ImageVector? = null,
    val activeColor: Color,
    val iconSize: androidx.compose.ui.unit.Dp = 24.dp,
    val selectedIconSize: androidx.compose.ui.unit.Dp = 26.dp,
)

private val appSections = listOf(
    AppSection(label = "岁月", iconRes = R.drawable.nav_timeline_woodblock, activeColor = Vermilion),
    AppSection(label = "人物", iconRes = R.drawable.nav_people_woodblock, activeColor = Vermilion),
    AppSection(
        label = "天下",
        vectorIcon = Icons.Outlined.Public,
        activeColor = Celadon,
        iconSize = 20.dp,
        selectedIconSize = 23.dp,
    ),
    AppSection(
        label = "我的",
        iconRes = R.drawable.nav_profile_woodblock,
        activeColor = Brass,
        // 头像原图的有效笔画范围比其他木刻图标更大；不改资源，仅按其
        // 实际留白校准到与时间、人物图标相同的视觉尺寸。
        iconSize = 19.dp,
        selectedIconSize = 21.dp,
    ),
)

@Composable
private fun TwoCapitalsApp(repository: MingRepository) {
    var selectedSection by rememberSaveable { mutableIntStateOf(0) }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = XuanPaper,
        bottomBar = {
            MingBottomBar(
                selectedSection = selectedSection,
                onSectionSelected = { selectedSection = it },
            )
        },
    ) { innerPadding ->
        var focusPerson by remember { mutableStateOf<String?>(null) }
        when (selectedSection) {
            0 -> TimelineScreen(
                repository = repository,
                contentPadding = innerPadding,
                onOpenPerson = { name ->
                    focusPerson = name
                    selectedSection = 1
                },
            )
            1 -> PeopleScreen(
                repository = repository,
                contentPadding = innerPadding,
                focusPerson = focusPerson,
                onFocusConsumed = { focusPerson = null },
            )
            2 -> WorldScreen(repository, innerPadding)
            else -> ProfileScreen(innerPadding)
        }
    }
}

@Composable
private fun MingBottomBar(selectedSection: Int, onSectionSelected: (Int) -> Unit) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .height(74.dp),
        color = PaperLight,
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.68f)),
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(start = 4.dp, top = 1.dp, end = 4.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.Top,
        ) {
            appSections.forEachIndexed { index, section ->
                val selected = selectedSection == index
                val tint = if (selected) section.activeColor else InkSoft
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { onSectionSelected(index) }
                        .padding(top = 1.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(1.dp),
                ) {
                    val iconSize = if (selected) section.selectedIconSize else section.iconSize
                    when {
                        section.vectorIcon != null -> Icon(
                            imageVector = section.vectorIcon,
                            contentDescription = section.label,
                            modifier = Modifier.size(iconSize),
                            tint = tint,
                        )

                        section.iconRes != null -> Image(
                            painter = painterResource(section.iconRes),
                            contentDescription = section.label,
                            // Keep the remaining woodblock icons within a consistent, smaller
                            // optical frame so their labels remain fully unobscured.
                            modifier = Modifier.size(iconSize),
                            contentScale = ContentScale.Inside,
                            colorFilter = ColorFilter.tint(tint),
                        )
                    }
                    Text(
                        text = section.label,
                        color = tint,
                        fontFamily = FontFamily.Serif,
                        fontSize = 13.sp,
                        lineHeight = 15.sp,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                    )
                }
                if (index != appSections.lastIndex) {
                    HorizontalDivider(
                        modifier = Modifier
                            .height(34.dp)
                            .width(1.dp),
                        color = LineGold.copy(alpha = 0.58f),
                    )
                }
            }
        }
    }
}

@Composable
private fun PeopleScreen(
    repository: MingRepository,
    contentPadding: PaddingValues,
    focusPerson: String? = null,
    onFocusConsumed: () -> Unit = {},
) {
    var selectedTab by rememberSaveable { mutableStateOf(PeopleTab.DYNASTY) }
    var selectedCategory by rememberSaveable { mutableStateOf(PersonCategory.EMPERORS) }
    var selectedReignTitle by rememberSaveable { mutableStateOf("洪武") }
    var query by rememberSaveable { mutableStateOf("") }
    var selectedPersonName by rememberSaveable { mutableStateOf<String?>(null) }
    var profileOrigin by rememberSaveable { mutableStateOf<String?>(null) }
    var personStack by rememberSaveable { mutableStateOf(listOf<String>()) }
    var relationView by rememberSaveable { mutableStateOf(RelationView.PERSON) }
    val reigns = remember(repository) { repository.reigns() }
    val relations = remember(repository) { repository.personRelations() }
    val allPeople = remember(repository) { repository.allPeople() }
    // 排序键含字符串解析，只在资料变化时算一次；搜索与切类目仅做线性过滤。
    val sortedPeople = remember(repository) {
        allPeople.sortedWith(compareBy({ personChronologyRank(it) }, { personBirthYear(it) }, { it.name }))
    }
    val allEvents = remember(reigns) { reigns.flatMap { it.events } }
    val selectedPerson = allPeople.firstOrNull { it.name == selectedPersonName }
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
    val people = remember(sortedPeople, selectedCategory, query) {
        val keyword = query.trim()
        sortedPeople.filter { person ->
            person.category == selectedCategory &&
                (keyword.isBlank() || person.name.contains(keyword) || person.title.contains(keyword) || person.reign.contains(keyword))
        }
    }

    fun returnFromProfile() {
        val origin = profileOrigin
        selectedPersonName = null
        profileOrigin = null
        personStack = emptyList()
        query = ""
        if (origin == "dynasty") selectedTab = PeopleTab.DYNASTY
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
                profileOrigin = "people"
                personStack = emptyList()
            }
            onFocusConsumed()
        }
    }

    // 人物履历打开后，系统返回键与页面内返回键保持同一行为，并恢复进入详情前的栏目。
    BackHandler(enabled = selectedPersonName != null) {
        closeProfileStep()
    }

    MingList(contentPadding) {
        item { MingMasthead() }
        item { OrnamentalTitle("人物") }
        item {
            PeopleTabRail(
                selected = selectedTab,
                onSelected = {
                    selectedTab = it
                    selectedPersonName = null
                    profileOrigin = null
                },
            )
        }
        when (selectedTab) {
            PeopleTab.DYNASTY -> {
                val selectedReign = reigns.firstOrNull { it.title == selectedReignTitle } ?: reigns.first()
                item {
                    ReignRail(reigns, selectedReign.title) { selectedReignTitle = it }
                }
                item {
                    DynastyArchive(
                        reign = selectedReign,
                        people = allPeople.filter { it.reign.contains(selectedReign.title) },
                        onPersonSelected = { person ->
                            selectedCategory = person.category
                            query = person.name
                            selectedPersonName = person.name
                            profileOrigin = "dynasty"
                            personStack = emptyList()
                            selectedTab = PeopleTab.PEOPLE
                        },
                    )
                }
            }
            PeopleTab.PEOPLE -> {
                val selectedPerson = allPeople.firstOrNull { it.name == selectedPersonName }
                if (selectedPerson != null) {
                    item {
                        PersonProfile(
                            person = profileDetail ?: selectedPerson,
                            relations = relations,
                            events = allEvents,
                            onBack = ::closeProfileStep,
                            onOpenPerson = ::openRelatedPerson,
                        )
                    }
                } else {
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
                    item { PersonChronologyRail(reigns) }
                    if (people.isEmpty()) {
                        item { SourceNote("没有相符人物。可搜索姓名、身份或年号。") }
                    } else {
                        items(people, key = { it.name }) { person ->
                            PersonCard(
                                person = person,
                                children = childrenByPerson[person.name].orEmpty(),
                                expanded = false,
                                onClick = {
                                    selectedPersonName = person.name
                                    profileOrigin = "people"
                                    personStack = emptyList()
                                },
                            )
                        }
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

@Composable
private fun PersonProfile(
    person: HistoricalPerson,
    relations: List<PersonRelation>,
    events: List<HistoricalEvent>,
    onBack: () -> Unit,
    onOpenPerson: (String) -> Unit,
) {
    val lifeSection = person.sections.firstOrNull { it.key == "life" }
    val familySection = person.sections.firstOrNull { it.key == "family" }
    val children = relations
        .filter { it.fromName == person.name && it.type in parentChildTypes() }
        .map { it.toName }
    val life = lifeSection?.content?.takeIf { it.isNotBlank() } ?: person.biography
    val family = familySection?.content?.takeIf { it.isNotBlank() }
        ?: listOf(person.familySummary, children.joinToString("、"))
            .filter { it.isNotBlank() }
            .joinToString("\n")
            .ifBlank { "家族、配偶与子嗣资料正在整理。" }
    // 关系与事件按人物交叉索引；没有记录时给出指向「关系」页的引导，避免空栏目。
    val personRelations = relations
        .filter { it.fromName == person.name || it.toName == person.name }
        .map { relation ->
            relation to (if (relation.fromName == person.name) relation.toName else relation.fromName)
        }
    val relatedEvents = events
        .filter { event -> event.participants.any { it == person.name } }
        .sortedBy { it.year ?: Int.MAX_VALUE }
        .map { event -> "${event.year?.toString() ?: "年份待考"} · ${event.title}\n${event.description}" }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(11.dp),
        ) {
            Text(
                "← 返回",
                modifier = Modifier
                    .align(Alignment.Start)
                    .clip(CutCornerShape(5.dp))
                    .clickable(onClick = onBack)
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium,
            )
            PersonPortrait(person)
            Text(person.name, color = Ink, fontFamily = FontFamily.Serif, fontSize = 30.sp, fontWeight = FontWeight.Bold)
            Text("${person.title}｜${person.reign}｜${person.years}", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 15.sp, textAlign = TextAlign.Center)
            LifeSection(life)
            // 没有实料的栏目不占位：家族占位文案、空关系、空事件均整栏隐藏。
            if (family.isNotBlank() && !family.contains("史料未见详载")) {
                ProfileSection("家族", readableParagraphs(family))
            }
            // 帝王条目不显示人物关系（宗室家庭资料在家族与子嗣栏呈现）。
            // 人物关系栏不含父子/母子（归家族栏）；帝王条目整栏不显示。
            val shownRelations = relations.filter {
                it.type !in parentChildTypes()
            }
            if (person.category != PersonCategory.EMPERORS && shownRelations.isNotEmpty()) {
                RelationSection(
                    shownRelations.map { relation ->
                        relation to (if (relation.fromName == person.name) relation.toName else relation.fromName)
                    },
                    onOpenPerson,
                )
            }
            if (relatedEvents.isNotEmpty()) {
                ProfileSection("相关事件", relatedEvents)
            }
        }
    }
}

/** 生平栏目：维基长文按小标题分块，超长默认截断，可展开全文；《明史》原文块单独标色。 */
@Composable
private fun LifeSection(content: String) {
    val blocks = remember(content) { parseLifeBlocks(content) }
    var expanded by remember(content) { mutableStateOf(false) }
    val limit = 1500
    val total = content.length
    Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("生平", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        var used = 0
        var truncated = false
        for (block in blocks) {
            if (!expanded && used > limit) {
                truncated = true
                break
            }
            when {
                block.isClassicalMarker -> Text(
                    block.text,
                    modifier = Modifier.padding(top = 8.dp),
                    color = Brass,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                )
                block.isHeader -> Text(
                    block.text,
                    modifier = Modifier.padding(top = 7.dp),
                    color = Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                )
                else -> Text(
                    block.text,
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 26.sp,
                    textAlign = TextAlign.Justify,
                )
            }
            used += block.text.length
        }
        if (truncated) {
            Text(
                "展开全文（共 $total 字）",
                modifier = Modifier
                    .clip(CutCornerShape(5.dp))
                    .clickable { expanded = true }
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = Celadon,
                fontFamily = FontFamily.SansSerif,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
            )
        } else if (total > limit) {
            Text(
                "收起",
                modifier = Modifier
                    .clip(CutCornerShape(5.dp))
                    .clickable { expanded = false }
                    .padding(horizontal = 4.dp, vertical = 6.dp),
                color = Brass,
                fontFamily = FontFamily.SansSerif,
                fontSize = 13.sp,
            )
        }
    }
}

@Composable
private fun ProfileSection(title: String, paragraphs: List<String>) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            paragraphs.forEach { paragraph ->
                Text(
                    text = paragraph,
                    color = InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 26.sp,
                    textAlign = TextAlign.Justify,
                )
            }
        }
    }
}

/** 人物详情里的关系条目：点击任意一条即跳转到对方的人物详情。 */
@Composable
private fun RelationSection(relations: List<Pair<PersonRelation, String>>, onOpenPerson: (String) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text("人物关系", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
        if (relations.isEmpty()) {
            Text(
                "暂无已编关系，可到「关系」页查看全量人物网络。",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                lineHeight = 26.sp,
            )
            return@Column
        }
        Text(
            "轻触条目，可跳转到对应人物",
            color = Brass,
            fontFamily = FontFamily.SansSerif,
            fontSize = 11.sp,
        )
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            relations.forEach { (relation, otherName) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(CutCornerShape(5.dp))
                        .clickable { onOpenPerson(otherName) }
                        .padding(horizontal = 4.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            "「${relation.type.label}」$otherName",
                            color = Ink,
                            fontFamily = FontFamily.Serif,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium,
                        )
                        if (relation.note.isNotBlank()) {
                            Text(
                                relation.note,
                                color = InkSoft,
                                fontFamily = FontFamily.Serif,
                                fontSize = 13.sp,
                                lineHeight = 20.sp,
                            )
                        }
                    }
                    Text(
                        "›",
                        color = Brass,
                        fontFamily = FontFamily.Serif,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun DynastyArchive(
    reign: Reign,
    people: List<HistoricalPerson>,
    onPersonSelected: (HistoricalPerson) -> Unit,
) {
    // 本朝人物按六分类全量归档：朝臣、将帅之外，封爵、内廷、文苑与帝王同列，避免遗漏。
    val groups = PersonCategory.entries.map { category -> category to people.filter { it.category == category } }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.95f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("${reign.title}朝档案", color = Ink, fontFamily = FontFamily.Serif, fontSize = 25.sp, fontWeight = FontWeight.Bold)
            Text(reign.summary, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 23.sp)
            Text(
                "本朝已编 ${people.size} 人、${reign.events.size} 件大事；人物按六分类全量入档。",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
            )
            groups.forEach { (category, members) ->
                ArchiveGroup(category.label, category.subtitle, members, onPersonSelected)
            }
            Text("本朝大事", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            if (reign.events.isEmpty()) {
                Text("该朝事件正在按年份与史料卷次整理。", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
            } else {
                reign.events.sortedBy { it.year ?: Int.MAX_VALUE }.forEach { event ->
                    Surface(
                        color = XuanPaper.copy(alpha = 0.68f),
                        shape = CutCornerShape(6.dp),
                        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.75f)),
                    ) {
                        Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text("${event.year ?: ""} ${event.month} · ${event.title}", color = Ink, fontFamily = FontFamily.Serif, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            Text(event.description, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 20.sp)
                            if (event.participants.isNotEmpty()) {
                                Text("相关人物：${event.participants.joinToString("、")}", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ArchiveGroup(
    title: String,
    hint: String,
    people: List<HistoricalPerson>,
    onPersonSelected: (HistoricalPerson) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.width(7.dp))
            Text(hint, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 12.sp)
        }
        if (people.isEmpty()) {
            Text("本朝暂无已编人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                items(people, key = { it.name }) { person ->
                    Surface(
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { onPersonSelected(person) },
                        shape = CutCornerShape(5.dp),
                        color = PaperShade,
                        border = BorderStroke(1.dp, LineGold),
                    ) {
                        Column(modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp)) {
                            Text(person.name, color = Ink, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                            Text(person.title, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PersonChronologyRail(reigns: List<Reign>) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = PaperLight.copy(alpha = 0.62f),
        shape = CutCornerShape(6.dp),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.8f)),
    ) {
        Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("人物年表", color = Ink, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.width(8.dp))
                Text("按所处时代排序", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
            }
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 5.dp),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                items(reigns, key = { it.title }) { reign ->
                    val firstYear = reign.yearRange.substringBefore("—")
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Surface(
                            modifier = Modifier.size(if (reign.title == "洪武") 8.dp else 6.dp),
                            shape = RoundedCornerShape(50),
                            color = if (reign.title == "洪武") Vermilion else Brass,
                        ) {}
                        Column {
                            Text(reign.title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 11.sp, fontWeight = FontWeight.Bold)
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
private fun WorldScreen(repository: MingRepository, contentPadding: PaddingValues) {
    var worldSection by rememberSaveable { mutableStateOf(WorldSection.MAP) }
    var modernOverlayEnabled by rememberSaveable { mutableStateOf(false) }
    val specials = repository.specialItems()
    val relicGroups = remember(specials) {
        listOf("制度", "器物", "习俗", "宫阙", "陵寝", "专题")
            .map { cat -> cat to specials.filter { it.category == cat } }
            .filter { it.second.isNotEmpty() }
    }

    MingList(contentPadding) {
        item { MingMasthead() }
        item { OrnamentalTitle("天下") }
        item {
            WorldSectionRail(
                selected = worldSection,
                onSelected = { worldSection = it },
            )
        }
        when (worldSection) {
            WorldSection.MAP -> {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(460.dp)
                            .clip(CutCornerShape(10.dp))
                            .background(XuanPaper),
                    ) {
                        Image(
                            painter = painterResource(R.drawable.world_reference_screen),
                            contentDescription = "明代两京十三省地图",
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop,
                            alignment = Alignment.Center,
                        )
                        if (modernOverlayEnabled) {
                            Image(
                                painter = painterResource(R.drawable.modern_reference_map),
                                contentDescription = "现代区划对照图已叠加",
                                modifier = Modifier
                                    .fillMaxSize()
                                    .alpha(0.68f),
                                contentScale = ContentScale.Crop,
                                alignment = Alignment.Center,
                            )
                        }
                        Surface(
                            modifier = Modifier
                                .align(Alignment.BottomEnd)
                                .padding(12.dp),
                            shape = RoundedCornerShape(50),
                            color = PaperLight.copy(alpha = 0.94f),
                            border = BorderStroke(1.dp, Brass.copy(alpha = 0.55f)),
                        ) {
                            IconButton(
                                onClick = { modernOverlayEnabled = !modernOverlayEnabled },
                                modifier = Modifier.size(44.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.Layers,
                                    contentDescription = "切换现代区划图层",
                                    tint = Ink,
                                )
                            }
                        }
                    }
                }
                item {
                    SourceNote("舆图为经确认的明代两京十三省参考图；右下角按钮叠加现代区划对照（临时示意），后续以真实现代图层替换。")
                }
            }
            WorldSection.INSTITUTIONS -> {
                item { InstitutionIntro() }
                items(repository.institutions(), key = { it.id }) { institution ->
                    InstitutionCard(institution)
                }
            }
            WorldSection.RELICS -> {
                if (specials.isEmpty()) {
                    item { SourceNote("典章科普内容将在内容服务载入后显示。") }
                } else {
                    relicGroups.forEach { (category, items) ->
                        item(key = "relics-header-$category") {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(category, color = Ink, fontFamily = FontFamily.Serif, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                                Spacer(Modifier.width(7.dp))
                                Text("共 ${items.size} 篇", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                            }
                        }
                        items(items, key = { it.id }) { item ->
                            SpecialItemCard(item)
                        }
                    }
                }
            }
        }
    }
}

/** 天下页的三个栏目：舆图 / 机构 / 典章。 */
private enum class WorldSection(val label: String) {
    MAP("舆图"),
    INSTITUTIONS("机构"),
    RELICS("典章"),
}

@Composable
private fun WorldSectionRail(selected: WorldSection, onSelected: (WorldSection) -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = PaperLight.copy(alpha = 0.88f),
        shape = CutCornerShape(8.dp),
        border = BorderStroke(1.dp, LineGold),
    ) {
        Row(modifier = Modifier.padding(4.dp)) {
            WorldSection.entries.forEach { section ->
                val active = section == selected
                Text(
                    text = section.label,
                    modifier = Modifier
                        .weight(1f)
                        .clip(CutCornerShape(5.dp))
                        .clickable { onSelected(section) }
                        .background(if (active) Celadon else Color.Transparent)
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
private fun SpecialItemCard(item: SpecialItem) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(item.name, color = Ink, modifier = Modifier.weight(1f), fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                Seal(item.category)
            }
            Text(item.era, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(item.description, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 23.sp, textAlign = TextAlign.Justify)
        }
    }
}

@Composable
private fun ProfileScreen(contentPadding: PaddingValues) {
    MingList(contentPadding) {
        item { MingMasthead() }
        item { OrnamentalTitle("我的") }
        item {
            ProfileCard(
                title = "我的书案",
                description = "登录后可同步收藏、阅读进度与自建专题。",
                icon = Icons.Outlined.BookmarkBorder,
                action = "查看收藏",
            )
        }
        item {
            ProfileCard(
                title = "离线资料包",
                description = "当前为首批演示资料。正式版本支持按专题下载，并在本机加密缓存。",
                icon = Icons.Outlined.Download,
                action = "资料管理",
            )
        }
        item {
            SourceNote("历史资料以来源为先。未标卷次与出处的内容只作为导览，不作为定论。")
        }
    }
}

@Composable
private fun CategoryRail(selectedCategory: PersonCategory, onSelected: (PersonCategory) -> Unit) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(PersonCategory.entries, key = { it.name }) { category ->
            val selected = category == selectedCategory
            Surface(
                modifier = Modifier
                    .widthIn(min = 88.dp)
                    .clip(CutCornerShape(8.dp))
                    .clickable { onSelected(category) },
                color = if (selected) Vermilion else PaperLight,
                shape = CutCornerShape(8.dp),
                border = BorderStroke(1.dp, if (selected) Vermilion else LineGold),
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = category.label,
                        color = if (selected) PaperLight else Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 20.sp,
                        textAlign = TextAlign.Center,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = category.subtitle,
                        color = if (selected) PaperLight.copy(alpha = 0.85f) else InkSoft,
                        fontFamily = FontFamily.Serif,
                        fontSize = 10.sp,
                        lineHeight = 13.sp,
                    )
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
private fun RelationshipNetwork(relations: List<PersonRelation>) {
    val focusNames = remember(relations) {
        relations
            .flatMap { listOf(it.fromName, it.toName) }
            .distinct()
            .sorted()
    }
    val defaultFocus = remember(relations) {
        focusNames.maxByOrNull { name -> relations.count { it.fromName == name || it.toName == name } }.orEmpty()
    }
    var selectedFocus by rememberSaveable { mutableStateOf(defaultFocus) }
    val activeFocus = selectedFocus.takeIf { it in focusNames } ?: defaultFocus
    val focusedRelations = relations.filter { it.fromName == activeFocus || it.toName == activeFocus }
    val neighbours = focusedRelations.map { relation ->
        if (relation.fromName == activeFocus) relation.toName else relation.fromName
    }.distinct()
    val legend = focusedRelations.map { it.type }.distinct().map { it to it.label }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("人物关系图", color = Ink, fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
            Text(
                "按后端已编目的关系连线。选择一位人物，查看其直接关联；节点位置只为阅读布局，不代表地理位置或政治距离。",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                lineHeight = 21.sp,
            )
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(7.dp),
                contentPadding = PaddingValues(horizontal = 1.dp),
            ) {
                items(focusNames, key = { it }) { name ->
                    val selected = name == activeFocus
                    Surface(
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { selectedFocus = name },
                        shape = CutCornerShape(5.dp),
                        color = if (selected) Celadon else PaperShade,
                        border = BorderStroke(1.dp, if (selected) Celadon else LineGold),
                    ) {
                        Text(
                            text = name,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            color = if (selected) PaperLight else Ink,
                            fontFamily = FontFamily.Serif,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(if (neighbours.size > 6) 360.dp else 280.dp)
                    .clip(CutCornerShape(8.dp))
                    .background(XuanPaper),
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val center = androidx.compose.ui.geometry.Offset(size.width / 2f, size.height / 2f)
                    val neighbourCenters = neighbours.mapIndexed { index, _ ->
                        val angle = -Math.PI / 2 + (Math.PI * 2 * index / neighbours.size.coerceAtLeast(1))
                        androidx.compose.ui.geometry.Offset(
                            x = center.x + size.width * .39f * cos(angle).toFloat(),
                            y = center.y + size.height * .36f * sin(angle).toFloat(),
                        )
                    }
                    focusedRelations.forEachIndexed { index, relation ->
                        drawLine(
                            color = relationshipColor(relation.type).copy(alpha = .72f),
                            start = center,
                            end = neighbourCenters[index],
                            strokeWidth = if (relation.type == RelationshipType.RULER_MINISTER) 3.dp.toPx() else 2.dp.toPx(),
                            cap = StrokeCap.Round,
                        )
                    }
                }
                RelationshipNode(
                    name = activeFocus,
                    emphasized = true,
                    modifier = Modifier.align(Alignment.Center),
                )
                neighbours.forEachIndexed { index, name ->
                    val angle = -Math.PI / 2 + (Math.PI * 2 * index / neighbours.size.coerceAtLeast(1))
                    RelationshipNode(
                        name = name,
                        emphasized = false,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .offset(
                                x = maxWidth / 2 + maxWidth * .39f * cos(angle).toFloat() - 30.dp,
                                y = maxHeight / 2 + maxHeight * .36f * sin(angle).toFloat() - 16.dp,
                            ),
                    )
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                legend.forEach { (type, label) ->
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                        Surface(modifier = Modifier.size(8.dp), shape = RoundedCornerShape(50), color = relationshipColor(type)) {}
                        Text(label, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                    }
                }
            }
            Text(
                "已建立 ${relations.size} 条首批关系；当前显示“$activeFocus”关联的 ${focusedRelations.size} 条，可横向选择其他人物继续查看。",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 13.sp,
            )
        }
    }
}

private fun relationshipColor(type: RelationshipType): Color = when (type) {
    RelationshipType.RULER_MINISTER -> Vermilion
    RelationshipType.COMMAND -> Indigo
    RelationshipType.COLLEAGUE -> Brass
    RelationshipType.RIVAL -> InkSoft
    RelationshipType.MENTOR -> Celadon
    RelationshipType.PARENT_CHILD -> Vermilion
    RelationshipType.MOTHER_CHILD -> Vermilion
    RelationshipType.SPOUSE -> Celadon
    RelationshipType.SIBLING -> Brass
}

@Composable
private fun RelationshipNode(name: String, emphasized: Boolean, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = CutCornerShape(5.dp),
        color = if (emphasized) Celadon else PaperLight,
        border = BorderStroke(1.dp, if (emphasized) Celadon else Brass),
    ) {
        Text(
            text = name,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp),
            color = if (emphasized) PaperLight else Ink,
            fontFamily = FontFamily.Serif,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

/** 关系页的双视图：人物关系网络与事件关系网络。 */
private enum class RelationView(val label: String) {
    PERSON("人物关系"),
    EVENT("事件关系"),
}

@Composable
private fun RelationViewRail(selected: RelationView, onSelected: (RelationView) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        RelationView.entries.forEach { view ->
            val active = view == selected
            Surface(
                modifier = Modifier
                    .clip(CutCornerShape(6.dp))
                    .clickable { onSelected(view) },
                shape = CutCornerShape(6.dp),
                color = if (active) Celadon else PaperLight,
                border = BorderStroke(1.dp, if (active) Celadon else LineGold),
            ) {
                Text(
                    text = view.label,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 9.dp),
                    color = if (active) PaperLight else Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

/** 事件为中心的辐射图：辐条一端是参与人物，另一端是共享人物的其他事件。 */
@Composable
private fun EventRelationshipNetwork(events: List<HistoricalEvent>) {
    val graphEvents = remember(events) { events.filter { it.participants.isNotEmpty() } }
    val defaultFocusId = remember(graphEvents) {
        graphEvents.maxByOrNull { it.participants.size }?.id.orEmpty()
    }
    var selectedFocusId by rememberSaveable { mutableStateOf(defaultFocusId) }
    val focus = graphEvents.firstOrNull { it.id == selectedFocusId } ?: graphEvents.firstOrNull()
    val participants = focus?.participants.orEmpty().take(8)
    val relatedEvents = remember(focus) {
        focus
            ?.let { event ->
                graphEvents
                    .filter { other -> other.id != event.id && other.participants.any { it in event.participants } }
                    .sortedByDescending { other -> other.participants.count { it in event.participants } }
                    .take(8)
            }
            .orEmpty()
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(10.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("事件关系图", color = Ink, fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
            Text(
                "以事件为中心：红线连出参与人物，褐线连出与其共享人物的其他事件。选择下方任一事件继续查看。",
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                lineHeight = 21.sp,
            )
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(7.dp),
                contentPadding = PaddingValues(horizontal = 1.dp),
            ) {
                items(graphEvents, key = { it.id }) { event ->
                    val selected = event.id == focus?.id
                    Surface(
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { selectedFocusId = event.id },
                        shape = CutCornerShape(5.dp),
                        color = if (selected) Celadon else PaperShade,
                        border = BorderStroke(1.dp, if (selected) Celadon else LineGold),
                    ) {
                        Text(
                            text = "${event.year ?: "年份待考"}·${event.title}",
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            color = if (selected) PaperLight else Ink,
                            fontFamily = FontFamily.Serif,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
            val spokeCount = participants.size + relatedEvents.size
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(if (spokeCount > 6) 360.dp else 280.dp)
                    .clip(CutCornerShape(8.dp))
                    .background(XuanPaper),
            ) {
                val eventColor = Brass
                val personColor = Vermilion
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val center = androidx.compose.ui.geometry.Offset(size.width / 2f, size.height / 2f)
                    val spokes = participants.map { it to personColor } + relatedEvents.map { it.title to eventColor }
                    spokes.forEachIndexed { index, (_, color) ->
                        val angle = -Math.PI / 2 + (Math.PI * 2 * index / spokeCount.coerceAtLeast(1))
                        drawLine(
                            color = color.copy(alpha = .72f),
                            start = center,
                            end = androidx.compose.ui.geometry.Offset(
                                x = center.x + size.width * .39f * cos(angle).toFloat(),
                                y = center.y + size.height * .36f * sin(angle).toFloat(),
                            ),
                            strokeWidth = 2.dp.toPx(),
                            cap = StrokeCap.Round,
                        )
                    }
                }
                if (focus != null) {
                    RelationshipNode(
                        name = "${focus.year ?: ""} ${focus.title}",
                        emphasized = true,
                        modifier = Modifier.align(Alignment.Center),
                    )
                }
                val spokes = participants.map { it to personColor } + relatedEvents.map { it.title to eventColor }
                spokes.forEachIndexed { index, (label, _) ->
                    val angle = -Math.PI / 2 + (Math.PI * 2 * index / spokeCount.coerceAtLeast(1))
                    RelationshipNode(
                        name = label,
                        emphasized = false,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .offset(
                                x = maxWidth / 2 + maxWidth * .39f * cos(angle).toFloat() - 30.dp,
                                y = maxHeight / 2 + maxHeight * .36f * sin(angle).toFloat() - 16.dp,
                            ),
                    )
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Surface(modifier = Modifier.size(8.dp), shape = RoundedCornerShape(50), color = Vermilion) {}
                    Text("参与人物", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Surface(modifier = Modifier.size(8.dp), shape = RoundedCornerShape(50), color = Brass) {}
                    Text("关联事件", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
                }
            }
            Text(
                "「${focus?.year ?: "年份待考"} ${focus?.title.orEmpty()}」参与人物 ${participants.size} 位；与其共享人物的事件 ${relatedEvents.size} 件。",
                color = Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 13.sp,
            )
        }
    }
}

@Composable
private fun RelationshipLedger(relations: List<PersonRelation>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column {
            Row(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("关系簿", color = Ink, modifier = Modifier.weight(1f), fontFamily = FontFamily.Serif, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text("按时代标注", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 13.sp)
            }
            relations.forEachIndexed { index, relation ->
                if (index > 0) HorizontalDivider(color = LineGold.copy(alpha = .65f))
                Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = "${relation.fromName}  ·  ${relation.type.label}  ·  ${relation.toName}",
                        color = Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text("${relation.reign}｜${relation.note}", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 21.sp)
                }
            }
        }
    }
}

@Composable
private fun InstitutionIntro() {
    SourceNote("机构页按“中央政务、监察司法、军事卫所、内廷宦官、地方治理”归档。晋升路径是制度导览，具体授官仍以品秩、差遣与实录记载为准。")
}

@Composable
private fun InstitutionCard(institution: Institution) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = .96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(institution.name, color = Ink, modifier = Modifier.weight(1f), fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                Seal(institution.category)
            }
            Text(institution.activeReigns, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(institution.function, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 23.sp)
            Text("晋升导览", color = Ink, fontFamily = FontFamily.Serif, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                items(institution.promotionPath) { step ->
                    Surface(shape = CutCornerShape(4.dp), color = PaperShade, border = BorderStroke(1.dp, LineGold)) {
                        Text(step, modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp), color = Ink, fontFamily = FontFamily.Serif, fontSize = 13.sp)
                    }
                }
            }
            if (institution.reforms.isNotEmpty()) {
                Text("制度变革", color = Ink, fontFamily = FontFamily.Serif, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                institution.reforms.forEach { reform ->
                    Text("${reform.year} · ${reform.title}：${reform.description}", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 21.sp)
                }
            }
        }
    }
}

private val PersonCardPortraitWidth = 116.dp
private val PersonCardPortraitHeight = 160.dp

@Composable
private fun PersonCard(
    person: HistoricalPerson,
    children: List<String>,
    expanded: Boolean,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize()
            .clickable(onClick = onClick),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.95f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Row(
            // Portrait slots never grow from the source image's intrinsic ratio.
            // The text side may grow for an expanded biography, but each image
            // remains the same measured frame throughout the people catalogue.
            modifier = Modifier.heightIn(min = PersonCardPortraitHeight),
            verticalAlignment = Alignment.Top,
        ) {
            PersonPortrait(person)
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 10.dp, top = 16.dp, end = 14.dp, bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = person.name,
                        color = Ink,
                        modifier = Modifier.weight(1f),
                        fontFamily = FontFamily.Serif,
                        fontSize = 25.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text("›", color = Brass, fontFamily = FontFamily.Serif, fontSize = 32.sp)
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    HorizontalDivider(modifier = Modifier.width(26.dp), color = Brass)
                    Text(
                        text = "  ${person.reign}  ",
                        color = Vermilion,
                        fontFamily = FontFamily.Serif,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    HorizontalDivider(modifier = Modifier.width(26.dp), color = Brass)
                }
                Text(person.title, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
                Text(person.years, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
                if (expanded) {
                    HorizontalDivider(modifier = Modifier.padding(top = 5.dp), color = LineGold)
                    if (person.courtesyName.isNotBlank()) {
                        Text("字（号）：${person.courtesyName}", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    }
                    Text(person.biography, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 22.sp)
                    if (children.isNotEmpty()) {
                        Text(
                            "已编子嗣（${children.size}）：${children.joinToString("、")}",
                            color = Vermilion,
                            fontFamily = FontFamily.Serif,
                            fontSize = 14.sp,
                            lineHeight = 21.sp,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PersonPortrait(person: HistoricalPerson) {
    val resource = when (person.portraitKey ?: person.name) {
        "朱元璋" -> R.drawable.portrait_zhuyuanzhang
        "朱允炆" -> R.drawable.portrait_zhuyunwen
        "朱棣" -> R.drawable.portrait_zhudi
        "朱瞻基" -> R.drawable.portrait_zhuzhanji
        "刘基" -> R.drawable.portrait_liuji
        "徐达" -> R.drawable.portrait_xuda
        "于谦" -> R.drawable.portrait_yuqian
        "张居正" -> R.drawable.portrait_zhangjuzheng
        "郑和" -> R.drawable.portrait_zhenghe
        "戚继光" -> R.drawable.portrait_qijiguang
        "秦良玉" -> R.drawable.portrait_qinliangyu
        "孙传庭" -> R.drawable.portrait_sunchuanting
        "李时珍" -> R.drawable.portrait_lishizhen
        else -> null
    }
    Box(
        modifier = Modifier
            .width(PersonCardPortraitWidth)
            .height(PersonCardPortraitHeight)
            .background(PaperShade.copy(alpha = 0.46f)),
        contentAlignment = Alignment.BottomCenter,
    ) {
        if (resource != null) {
            Image(
                painter = painterResource(resource),
                contentDescription = "${person.name}插绘",
                modifier = Modifier
                    .fillMaxSize()
                    .padding(top = 4.dp),
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter,
            )
        } else {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Icon(Icons.Outlined.PersonOutline, null, modifier = Modifier.size(52.dp), tint = Brass)
                Text("待补图像", color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun ProfileCard(title: String, description: String, icon: ImageVector, action: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, null, modifier = Modifier.size(34.dp), tint = Celadon)
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                Text(description, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp, lineHeight = 22.sp)
                Text(action, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Preview(showBackground = true, heightDp = 840)
@Composable
private fun TwoCapitalsAppPreview() {
    两京一十三省Theme {
        TwoCapitalsApp(repository = SeedMingRepository)
    }
}
