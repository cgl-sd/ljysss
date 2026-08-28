package com.ljyss

import android.os.Bundle
import android.util.Log
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
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.DateRange
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.Layers
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.Map
import androidx.compose.material.icons.outlined.Menu
import androidx.compose.material.icons.outlined.PersonOutline
import androidx.compose.material.icons.outlined.Public
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.foundation.gestures.detectDragGestures
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
import com.ljyss.data.model.MapLabel
import com.ljyss.data.model.MapLabelAnchor
import com.ljyss.data.model.MapLayer
import com.ljyss.data.model.MapPeriod
import com.ljyss.data.model.PeopleTab
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.RelationshipType
import com.ljyss.data.model.Institution
import com.ljyss.data.model.Reign
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
            Thread {
                runCatching { RemoteMingRepository.load("http://127.0.0.1:8000") }
                    .onSuccess { remote -> runOnUiThread { repository = remote } }
                    .onFailure { error -> Log.w("MingContent", "使用离线资料：内容服务未连接", error) }
            }.start()
        }
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
        iconSize = 20.dp,
        selectedIconSize = 22.dp,
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
        when (selectedSection) {
            0 -> TimelineScreen(repository, innerPadding)
            1 -> PeopleScreen(repository, innerPadding)
            2 -> WorldScreen(innerPadding)
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
private fun TimelineScreen(repository: MingRepository, contentPadding: PaddingValues) {
    val reigns = remember(repository) { repository.reigns() }
    var selectedTitle by rememberSaveable { mutableStateOf(reigns.first().title) }
    var selectedYear by rememberSaveable { mutableIntStateOf(reigns.first().startYear()) }
    var showSources by rememberSaveable { mutableStateOf(false) }
    var expandedEventId by rememberSaveable { mutableStateOf<String?>(null) }
    val selectedReign = reigns.first { it.title == selectedTitle }

    MingList(contentPadding) {
        item { MingMasthead() }
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
                showSources = showSources,
                onSourceClick = { showSources = !showSources },
                expandedEventId = expandedEventId,
                onEventClick = { eventId ->
                    expandedEventId = if (expandedEventId == eventId) null else eventId
                },
            )
        }
    }
}

private fun Reign.startYear(): Int = yearRange.substringBefore("—").toInt()

private fun Reign.endYear(): Int = yearRange.substringAfter("—", yearRange).toInt()

private fun Reign.yearLabel(year: Int): String =
    "$title${chineseYearNumber(year - startYear() + 1)}年 · $year"

private fun chineseYearNumber(value: Int): String {
    val digits = listOf("零", "一", "二", "三", "四", "五", "六", "七", "八", "九")
    return when {
        value < 10 -> if (value == 1) "元" else digits[value]
        value < 20 -> if (value == 10) "十" else "十${digits[value % 10]}"
        value % 10 == 0 -> "${digits[value / 10]}十"
        else -> "${digits[value / 10]}十${digits[value % 10]}"
    }
}

@Composable
private fun PeopleScreen(repository: MingRepository, contentPadding: PaddingValues) {
    var selectedTab by rememberSaveable { mutableStateOf(PeopleTab.PEOPLE) }
    var selectedCategory by rememberSaveable { mutableStateOf(PersonCategory.EMPERORS) }
    var query by rememberSaveable { mutableStateOf("") }
    var expandedPerson by rememberSaveable { mutableStateOf<String?>(null) }
    val people = repository.people(selectedCategory).filter { person ->
        val keyword = query.trim()
        keyword.isBlank() || person.name.contains(keyword) || person.title.contains(keyword) || person.reign.contains(keyword)
    }.sortedWith(compareBy({ personChronologyRank(it) }, { personBirthYear(it) }, { it.name }))

    MingList(contentPadding) {
        item { MingMasthead() }
        item { OrnamentalTitle("人物") }
        item {
            PeopleTabRail(selected = selectedTab, onSelected = { selectedTab = it })
        }
        when (selectedTab) {
            PeopleTab.PEOPLE -> {
                item {
                    CategoryRail(
                        selectedCategory = selectedCategory,
                        onSelected = {
                            selectedCategory = it
                            expandedPerson = null
                        },
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
                item { PersonChronologyRail(repository.reigns()) }
                item {
                    SourceNote("现收录 ${repository.allPeople().size} 位人物；未有传世肖像者使用“绢本示意像”并明确标注。")
                }
                if (people.isEmpty()) {
                    item { SourceNote("没有相符人物。可搜索姓名、身份或年号。") }
                } else {
                    items(people, key = { it.name }) { person ->
                        PersonCard(
                            person = person,
                            expanded = expandedPerson == person.name,
                            onClick = {
                                expandedPerson = if (expandedPerson == person.name) null else person.name
                            },
                        )
                    }
                }
            }
            PeopleTab.RELATIONSHIPS -> {
                item { RelationshipNetwork(repository.personRelations()) }
                item { RelationshipLedger(repository.personRelations()) }
            }
            PeopleTab.INSTITUTIONS -> {
                item { InstitutionIntro() }
                items(repository.institutions(), key = { it.id }) { institution ->
                    InstitutionCard(institution)
                }
            }
        }
    }
}

private fun personBirthYear(person: HistoricalPerson): Int =
    person.years.substringBefore("—").trim().toIntOrNull() ?: Int.MAX_VALUE

private val personEraOrder = listOf(
    "洪武", "建文", "永乐", "洪熙", "宣德", "正统", "景泰", "天顺", "成化",
    "弘治", "正德", "嘉靖", "隆庆", "万历", "泰昌", "天启", "崇祯",
)

private fun personChronologyRank(person: HistoricalPerson): Int =
    personEraOrder.indexOfFirst { era -> person.reign.contains(era) }.let { index ->
        if (index >= 0) index else Int.MAX_VALUE
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
private fun WorldScreen(contentPadding: PaddingValues) {
    var modernOverlayEnabled by rememberSaveable { mutableStateOf(false) }
    // Align the initial indicator with the baked-in 1368 marker on the static atlas.
    var timelineProgress by rememberSaveable { mutableStateOf(0.04f) }

    WorldReferenceMing(
        modernOverlayEnabled = modernOverlayEnabled,
        onModernOverlayToggle = {
            modernOverlayEnabled = !modernOverlayEnabled
        },
        timelineProgress = timelineProgress,
        onTimelineProgressChange = { timelineProgress = it.coerceIn(0f, 1f) },
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .padding(bottom = contentPadding.calculateBottomPadding()),
    )
}

/**
 * The Ming atlas remains one approved static composition. Interactions are transparent
 * hit areas over the original image, so the historical map itself is never redrawn.
 */
@Composable
private fun WorldReferenceMing(
    modernOverlayEnabled: Boolean,
    onModernOverlayToggle: () -> Unit,
    timelineProgress: Float,
    onTimelineProgressChange: (Float) -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier.background(XuanPaper)) {
        Image(
            painter = painterResource(R.drawable.world_reference_screen),
            contentDescription = "明代两京十三省地图",
            // 参考图本身已是经用户确认的 1:1 地图构图；只留极薄安全留白，不重绘其标题或图例。
            modifier = Modifier
                .fillMaxSize()
                .padding(top = 8.dp),
            contentScale = ContentScale.Crop,
            alignment = Alignment.Center,
        )

        if (modernOverlayEnabled) {
            Image(
                painter = painterResource(R.drawable.modern_reference_map),
                contentDescription = "现代区划对照图已叠加",
                modifier = Modifier
                    .fillMaxSize()
                    .padding(top = 8.dp)
                    // The modern map remains one complete comparison layer over the unchanged
                    // Ming reference image, while the time rail and event card stay visible.
                    .drawWithContent {
                        clipRect(
                            top = 104.dp.toPx(),
                            bottom = size.height - 212.dp.toPx(),
                        ) {
                            this@drawWithContent.drawContent()
                        }
                    }
                    .alpha(0.68f),
                contentScale = ContentScale.Crop,
                alignment = Alignment.Center,
            )
        }

        // Four original atlas tools: map, menu, locate and layers. The first three only
        // acknowledge a press for now; layers directly toggles the comparison overlay.
        WorldPressTarget(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(start = 12.dp, top = 18.dp)
                .size(48.dp),
            onClick = {},
        )
        WorldPressTarget(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(end = 12.dp, top = 18.dp)
                .size(48.dp),
            onClick = {},
        )
        WorldPressTarget(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 11.dp, bottom = 258.dp)
                .size(48.dp),
            onClick = {},
        )
        WorldPressTarget(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 11.dp, bottom = 204.dp)
                .size(48.dp),
            onClick = onModernOverlayToggle,
        )

        // The original rail stays visible; only its red current-time indicator is dynamic.
        Canvas(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 133.dp, start = 12.dp, end = 12.dp)
                .fillMaxWidth()
                .height(42.dp)
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDragStart = { offset -> onTimelineProgressChange(offset.x / size.width) },
                        onDrag = { change, _ -> onTimelineProgressChange(change.position.x / size.width) },
                    )
                },
        ) {
            val trackStart = 10.dp.toPx()
            val trackEnd = size.width - 10.dp.toPx()
            val indicatorX = trackStart + (trackEnd - trackStart) * timelineProgress
            drawCircle(color = PaperLight.copy(alpha = 0.9f), radius = 8.dp.toPx(), center = androidx.compose.ui.geometry.Offset(indicatorX, size.height / 2))
            drawCircle(color = Vermilion, radius = 5.dp.toPx(), center = androidx.compose.ui.geometry.Offset(indicatorX, size.height / 2))
        }

        // The event card is intentionally a press-only affordance until its detail view exists.
        WorldPressTarget(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(horizontal = 5.dp)
                .fillMaxWidth()
                .height(122.dp),
            onClick = {},
        )
    }
}

@Composable
private fun WorldPressTarget(modifier: Modifier, onClick: () -> Unit) {
    Box(
        modifier = modifier
            .clickable(interactionSource = null, indication = null, onClick = onClick),
    )
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
private fun MingList(
    contentPadding: PaddingValues,
    content: LazyListScope.() -> Unit,
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(XuanPaper),
        contentPadding = PaddingValues(
            start = 18.dp,
            top = 44.dp,
            end = 18.dp,
            bottom = contentPadding.calculateBottomPadding() + 20.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        content = content,
    )
}

@Composable
private fun MingMasthead() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Image(
            painter = painterResource(R.drawable.ding_map_emblem),
            contentDescription = "两京一十三省的鼎形图标",
            modifier = Modifier.size(38.dp),
            contentScale = ContentScale.Fit,
        )
        Spacer(Modifier.width(9.dp))
        Text(
            text = "两京一十三省",
            color = Ink,
            fontFamily = FontFamily.Serif,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp,
        )
        Spacer(Modifier.width(9.dp))
        Seal("集录")
    }
}

@Composable
private fun OrnamentalTitle(title: String) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            HorizontalDivider(modifier = Modifier.width(72.dp), color = Brass.copy(alpha = 0.7f))
            Text(
                text = "  $title  ",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 29.sp,
                fontWeight = FontWeight.Bold,
            )
            HorizontalDivider(modifier = Modifier.width(72.dp), color = Brass.copy(alpha = 0.7f))
        }
        Text("◇", color = Vermilion, fontSize = 15.sp)
    }
}

@Composable
private fun ReignRail(reigns: List<Reign>, selectedTitle: String, onSelected: (String) -> Unit) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(horizontal = 2.dp),
    ) {
        items(reigns, key = { it.title }) { reign ->
            val selected = reign.title == selectedTitle
            Surface(
                modifier = Modifier
                    .widthIn(min = 74.dp)
                    .clip(CutCornerShape(8.dp))
                    .clickable { onSelected(reign.title) },
                color = if (selected) Vermilion else PaperLight,
                shape = CutCornerShape(8.dp),
                border = BorderStroke(1.dp, if (selected) Vermilion else LineGold),
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = reign.title,
                        color = if (selected) PaperLight else Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = reign.yearRange.substringBefore("—"),
                        color = if (selected) PaperLight else InkSoft,
                        fontSize = 11.sp,
                    )
                }
            }
        }
    }
}

@Composable
private fun DynastyRangeBar() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("1368", color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 19.sp, fontWeight = FontWeight.Bold)
        HorizontalDivider(
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = 10.dp),
            color = Brass,
            thickness = 2.dp,
        )
        Text("1644", color = Ink, fontFamily = FontFamily.Serif, fontSize = 19.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun ReignYearRail(reign: Reign, selectedYear: Int, onSelected: (Int) -> Unit) {
    val eventCountByYear = remember(reign) {
        reign.events.groupingBy { it.year ?: reign.startYear() }.eachCount()
    }
    LazyRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
        contentPadding = PaddingValues(horizontal = 2.dp),
    ) {
        items((reign.startYear()..reign.endYear()).toList(), key = { it }) { year ->
            val selected = year == selectedYear
            val eventCount = eventCountByYear[year] ?: 0
            Surface(
                modifier = Modifier
                    .widthIn(min = 64.dp)
                    .clip(CutCornerShape(6.dp))
                    .clickable { onSelected(year) },
                color = if (selected) Celadon else PaperLight,
                shape = CutCornerShape(6.dp),
                border = BorderStroke(1.dp, if (selected) Celadon else LineGold.copy(alpha = .82f)),
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 7.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    Text(
                        text = if (year == reign.startYear()) "元年" else "${chineseYearNumber(year - reign.startYear() + 1)}年",
                        color = if (selected) PaperLight else Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "$year${if (eventCount > 0) " · $eventCount 事" else ""}",
                        color = if (selected) PaperLight.copy(alpha = .92f) else InkSoft,
                        fontFamily = FontFamily.Serif,
                        fontSize = 10.sp,
                    )
                }
            }
        }
    }
}

@Composable
private fun TimelineArchive(
    reign: Reign,
    selectedYear: Int,
    showSources: Boolean,
    onSourceClick: () -> Unit,
    expandedEventId: String?,
    onEventClick: (String) -> Unit,
) {
    val orderedEvents = reign.events.sortedWith(
        compareBy<HistoricalEvent>({ it.year ?: Int.MAX_VALUE }, { lunarMonthOrder(it.month) }, { it.title }),
    ).filter { (it.year ?: reign.startYear()) == selectedYear }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.95f)),
        border = BorderStroke(1.5.dp, Brass.copy(alpha = 0.8f)),
        shape = CutCornerShape(10.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Box(modifier = Modifier.heightIn(min = 430.dp)) {
            Image(
                painter = painterResource(R.drawable.timeline_mountain_ornament),
                contentDescription = null,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .height(125.dp),
                contentScale = ContentScale.FillWidth,
                alpha = 0.52f,
            )
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 14.dp, vertical = 18.dp),
                verticalArrangement = Arrangement.spacedBy(15.dp),
            ) {
                Text(
                    text = reign.yearLabel(selectedYear),
                    color = Vermilion,
                    fontFamily = FontFamily.Serif,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                )
                MonthLine(orderedEvents.map { it.month })
                Surface(
                    color = XuanPaper.copy(alpha = 0.72f),
                    shape = CutCornerShape(8.dp),
                    border = BorderStroke(1.dp, LineGold),
                ) {
                    if (orderedEvents.isEmpty()) {
                        EmptyYearState(reign = reign, selectedYear = selectedYear)
                    } else {
                        Column {
                            orderedEvents.forEachIndexed { index, event ->
                                val eventId = event.id.ifBlank { "${reign.title}:${event.title}" }
                                if (index > 0) HorizontalDivider(color = LineGold.copy(alpha = 0.75f))
                                EventRow(
                                    event = event,
                                    tone = if (index == 0) Vermilion else Indigo,
                                    expanded = expandedEventId == eventId,
                                    onClick = { onEventClick(eventId) },
                                )
                            }
                        }
                    }
                }
                Spacer(Modifier.weight(1f))
                Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    SourceButton(expanded = showSources, onClick = onSourceClick)
                }
                if (showSources) {
                    SourceNote("首批事件来自《明实录》资料索引；正式资料由后端返回卷次、版本、引文位置与置信度。")
                }
            }
        }
    }
}

@Composable
private fun EmptyYearState(reign: Reign, selectedYear: Int) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 18.dp, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("本年尚未编入导览事件", color = Ink, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Text(
            "${reign.yearLabel(selectedYear)} 的实录条目会随内容库校核后补入。",
            color = InkSoft,
            fontFamily = FontFamily.Serif,
            fontSize = 14.sp,
            textAlign = TextAlign.Center,
            lineHeight = 21.sp,
        )
    }
}

private fun lunarMonthOrder(month: String): Int = when (month) {
    "正月" -> 1
    "二月" -> 2
    "三月" -> 3
    "四月" -> 4
    "五月" -> 5
    "六月" -> 6
    "七月" -> 7
    "八月" -> 8
    "九月" -> 9
    "十月" -> 10
    "冬月", "十一月" -> 11
    "腊月", "十二月" -> 12
    else -> 13
}

@Composable
private fun MonthLine(activeMonths: List<String>) {
    Row(modifier = Modifier.fillMaxWidth()) {
        listOf("正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "冬月", "腊月").forEach { month ->
            val active = activeMonths.contains(month)
            Column(
                modifier = Modifier.weight(1f),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                Text(
                    text = month.take(2),
                    color = if (active) Vermilion else InkSoft,
                    fontFamily = FontFamily.Serif,
                    fontSize = 11.sp,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Normal,
                )
                Surface(
                    modifier = Modifier.size(if (active) 10.dp else 7.dp),
                    shape = RoundedCornerShape(50),
                    color = if (active) Vermilion else Brass,
                ) {}
            }
        }
    }
}

@Composable
private fun EventRow(event: HistoricalEvent, tone: Color, expanded: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Surface(shape = CutCornerShape(6.dp), color = tone) {
            Text(
                text = event.month,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 12.dp),
                color = PaperLight,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
            )
        }
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = event.title,
                    color = Ink,
                    modifier = Modifier.weight(1f),
                    fontFamily = FontFamily.Serif,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                )
                Icon(Icons.Outlined.LocationOn, event.place, modifier = Modifier.size(16.dp), tint = InkSoft)
                Text(event.place, color = InkSoft, fontSize = 13.sp)
            }
            Text(
                text = event.description,
                color = InkSoft,
                fontFamily = FontFamily.Serif,
                fontSize = 14.sp,
                lineHeight = 22.sp,
            )
            if (expanded) {
                HorizontalDivider(modifier = Modifier.padding(top = 5.dp), color = LineGold)
                Text(
                    text = event.detail,
                    color = Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 15.sp,
                    lineHeight = 23.sp,
                )
                if (event.participants.isNotEmpty()) {
                    Text(
                        text = "相关人物：${event.participants.joinToString("、")}",
                        color = Vermilion,
                        fontFamily = FontFamily.Serif,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
                if (event.consequence.isNotBlank()) {
                    Text(
                        text = "影响：${event.consequence}",
                        color = InkSoft,
                        fontFamily = FontFamily.Serif,
                        fontSize = 14.sp,
                        lineHeight = 21.sp,
                    )
                }
                Text(
                    text = "出处：${event.sourceLabel}",
                    color = Brass,
                    fontFamily = FontFamily.Serif,
                    fontSize = 13.sp,
                )
            }
        }
    }
}

@Composable
private fun SourceButton(expanded: Boolean, onClick: () -> Unit) {
    Surface(
        modifier = Modifier
            .widthIn(min = 176.dp)
            .clip(CutCornerShape(7.dp))
            .clickable(onClick = onClick),
        shape = CutCornerShape(7.dp),
        color = PaperLight,
        border = BorderStroke(1.dp, Brass),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 15.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(7.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.BookmarkBorder, null, tint = InkSoft, modifier = Modifier.size(20.dp))
            Text(
                text = if (expanded) "收起史料来源" else "史料来源",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
            )
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
                    .widthIn(min = 82.dp)
                    .clip(CutCornerShape(8.dp))
                    .clickable { onSelected(category) },
                color = if (selected) Vermilion else PaperLight,
                shape = CutCornerShape(8.dp),
                border = BorderStroke(1.dp, if (selected) Vermilion else LineGold),
            ) {
                Text(
                    text = category.label,
                    modifier = Modifier.padding(horizontal = 15.dp, vertical = 12.dp),
                    color = if (selected) PaperLight else Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 20.sp,
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
private fun PersonCard(person: HistoricalPerson, expanded: Boolean, onClick: () -> Unit) {
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
                    Text("资料：${person.sourceLabel}", color = Brass, fontFamily = FontFamily.Serif, fontSize = 13.sp, lineHeight = 20.sp)
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
private fun WorldTopBar(period: MapPeriod, onPeriodSelected: (MapPeriod) -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            MapRoundControl(Icons.Outlined.Map, "地图") {}
            Spacer(Modifier.weight(1f))
            Text(
                text = "两京一十三省",
                color = Ink,
                fontFamily = FontFamily.Serif,
                fontSize = 25.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp,
            )
            Spacer(Modifier.weight(1f))
            MapRoundControl(Icons.Outlined.Menu, "图层菜单") {}
        }
        Surface(
            shape = RoundedCornerShape(50),
            color = PaperLight.copy(alpha = 0.88f),
            border = BorderStroke(1.dp, Brass),
        ) {
            Row(modifier = Modifier.padding(2.dp)) {
                MapPeriod.entries.forEach { item ->
                    val selected = item == period
                    Text(
                        text = item.label,
                        modifier = Modifier
                            .clip(RoundedCornerShape(50))
                            .clickable { onPeriodSelected(item) }
                            .background(if (selected) Celadon else Color.Transparent)
                            .padding(horizontal = 21.dp, vertical = 0.dp),
                        color = if (selected) PaperLight else Ink,
                        fontFamily = FontFamily.Serif,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun MapRoundControl(icon: ImageVector, description: String, onClick: () -> Unit) {
    Surface(
        modifier = Modifier
            .size(32.dp)
            .clip(RoundedCornerShape(50))
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(50),
        color = PaperLight.copy(alpha = 0.88f),
        border = BorderStroke(1.dp, Brass.copy(alpha = 0.8f)),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(icon, description, modifier = Modifier.size(17.dp), tint = Celadon)
        }
    }
}

@Composable
private fun MapLegend(modifier: Modifier, period: MapPeriod) {
    Surface(
        modifier = modifier,
        color = PaperLight.copy(alpha = 0.9f),
        shape = CutCornerShape(6.dp),
        border = BorderStroke(1.dp, Brass.copy(alpha = 0.8f)),
    ) {
        Column(
            modifier = Modifier.padding(5.dp),
            verticalArrangement = Arrangement.spacedBy(3.dp),
        ) {
            Text("图例", color = Ink, fontFamily = FontFamily.Serif, fontSize = 11.sp, lineHeight = 10.sp, fontWeight = FontWeight.Bold)
            Text("● 两京", color = Vermilion, fontSize = 9.sp, lineHeight = 10.sp)
            Text("○ 省治", color = Ink, fontSize = 9.sp, lineHeight = 10.sp)
            Text(if (period == MapPeriod.MING) "〰 长城" else "— 省界", color = InkSoft, fontSize = 9.sp, lineHeight = 10.sp)
            Text("— 边界", color = InkSoft, fontSize = 9.sp, lineHeight = 10.sp)
            Text("⌁ 山脉", color = InkSoft, fontSize = 9.sp, lineHeight = 10.sp)
            Text("≈ 水域", color = InkSoft, fontSize = 9.sp, lineHeight = 10.sp)
        }
    }
}

@Composable
private fun MapPlaceLabels(labels: List<MapLabel>) {
    // All labels are positioned in the same normalized map frame.  This makes
    // the Ming and modern maps keep their visual geography when the device size
    // changes, instead of each period using a different set of screen offsets.
    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        labels.forEach { label ->
            when (label.anchor) {
                MapLabelAnchor.BEIJING -> MapCapitalLabel(
                    label.name,
                    Modifier
                        .align(Alignment.TopStart)
                        .offset(x = maxWidth * 0.565f, y = maxHeight * 0.245f),
                )

                MapLabelAnchor.NANJING -> MapCapitalLabel(
                    label.name,
                    Modifier
                        .align(Alignment.TopStart)
                        .offset(x = maxWidth * 0.670f, y = maxHeight * 0.425f),
                )

                else -> {
                    val position = mapLabelFramePosition(label.anchor)
                    MapProvinceLabel(
                        label = label,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .offset(x = maxWidth * position.first, y = maxHeight * position.second),
                    )
                }
            }
        }
    }
}

private fun mapLabelFramePosition(anchor: MapLabelAnchor): Pair<Float, Float> =
    when (anchor) {
        MapLabelAnchor.NORTH -> 0.585f to 0.155f
        MapLabelAnchor.WEST -> 0.285f to 0.340f
        MapLabelAnchor.CENTRAL -> 0.595f to 0.470f
        MapLabelAnchor.EAST -> 0.750f to 0.555f
        MapLabelAnchor.KOREA -> 0.835f to 0.275f
        else -> 0.5f to 0.5f
    }

@Composable
private fun MapProvinceLabel(label: MapLabel, modifier: Modifier) {
    Text(
        text = label.name,
        modifier = modifier
            .background(PaperLight.copy(alpha = 0.66f), RoundedCornerShape(3.dp))
            .padding(horizontal = 4.dp, vertical = 2.dp),
        color = Ink,
        fontFamily = FontFamily.Serif,
        fontSize = if (label.name.length > 3) 12.sp else 16.sp,
        fontWeight = FontWeight.Bold,
    )
}

@Composable
private fun MapCapitalLabel(name: String, modifier: Modifier) {
    Row(
        modifier = modifier
            .background(Vermilion, CutCornerShape(4.dp))
            .padding(horizontal = 6.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Surface(modifier = Modifier.size(7.dp), shape = RoundedCornerShape(50), color = PaperLight) {}
        Text(name, color = PaperLight, fontFamily = FontFamily.Serif, fontSize = 13.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun MapSideActions(modifier: Modifier) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        MapRoundControl(Icons.Outlined.LocationOn, "定位") {}
        MapRoundControl(Icons.Outlined.Layers, "切换图层") {}
    }
}

@Composable
private fun WorldSheet(
    featuredReign: Reign,
    timelineYears: List<String>,
    layers: List<MapLayer>,
    enabledLayers: List<String>,
    onLayerToggle: (MapLayer) -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp, bottomStart = 8.dp, bottomEnd = 8.dp),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = 0.97f)),
        border = BorderStroke(1.dp, Brass.copy(alpha = 0.72f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            HorizontalDivider(modifier = Modifier.width(36.dp).align(Alignment.CenterHorizontally), color = InkSoft, thickness = 3.dp)
            TimelineScale(timelineYears)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Seal("大明")
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(featuredReign.displayYear, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    Text(featuredReign.summary, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 15.sp)
                }
                Text("›", color = Brass, fontFamily = FontFamily.Serif, fontSize = 32.sp)
            }
            LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                items(layers, key = { it.id }) { layer ->
                    val enabled = enabledLayers.contains(layer.id)
                    Surface(
                        modifier = Modifier
                            .clip(CutCornerShape(5.dp))
                            .clickable { onLayerToggle(layer) },
                        shape = CutCornerShape(5.dp),
                        color = if (enabled) PaperShade else PaperLight,
                        border = BorderStroke(1.dp, if (enabled) Brass else LineGold.copy(alpha = 0.6f)),
                    ) {
                        Text(
                            text = layer.label,
                            modifier = Modifier.padding(horizontal = 9.dp, vertical = 7.dp),
                            color = if (enabled) Ink else InkSoft,
                            fontFamily = FontFamily.Serif,
                            fontSize = 13.sp,
                            fontWeight = if (enabled) FontWeight.Bold else FontWeight.Normal,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun TimelineScale(years: List<String>) {
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        years.forEachIndexed { index, year ->
            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(year, color = if (index == 0) Vermilion else InkSoft, fontFamily = FontFamily.Serif, fontSize = 11.sp, fontWeight = if (index == 0) FontWeight.Bold else FontWeight.Normal)
                Surface(
                    modifier = Modifier
                        .padding(top = 4.dp)
                        .size(if (index == 0) 10.dp else 6.dp),
                    shape = RoundedCornerShape(50),
                    color = if (index == 0) Vermilion else Brass,
                ) {}
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

@Composable
private fun SourceNote(text: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(7.dp),
        color = PaperShade,
        border = BorderStroke(1.dp, LineGold),
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(14.dp),
            color = InkSoft,
            fontFamily = FontFamily.Serif,
            fontSize = 15.sp,
            lineHeight = 23.sp,
        )
    }
}

@Composable
private fun Seal(text: String) {
    Surface(shape = CutCornerShape(4.dp), color = Vermilion) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp),
            color = PaperLight,
            fontFamily = FontFamily.Serif,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Preview(showBackground = true, heightDp = 840)
@Composable
private fun TwoCapitalsAppPreview() {
    两京一十三省Theme {
        TwoCapitalsApp(repository = SeedMingRepository)
    }
}
