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
import com.ljyss.ui.people.PeopleScreen
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
