package com.ljyss

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Public
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.MingRepository
import com.ljyss.data.BundledMingRepository
import com.ljyss.ui.people.PeopleScreen
import com.ljyss.ui.profile.ProfileScreen
import com.ljyss.ui.search.GlobalSearchScreen
import com.ljyss.ui.search.SearchDestination
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper
import com.ljyss.ui.theme.两京一十三省Theme
import com.ljyss.ui.timeline.TimelineScreen
import com.ljyss.ui.world.WorldScreen

class MainActivity : ComponentActivity() {
    private var repository by mutableStateOf<MingRepository?>(null)
    private var contentLoadError by mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            两京一十三省Theme {
                val currentRepository = repository
                if (currentRepository != null) {
                    TwoCapitalsApp(repository = currentRepository)
                } else {
                    ContentLibraryState(contentLoadError)
                }
            }
        }
        // 阅读端只读取随应用交付的统一资料库；FastAPI 仅用于内容编辑和开发调试。
        Thread {
            runCatching { BundledMingRepository.load(applicationContext) }
                .onSuccess { local -> runOnUiThread { repository = local } }
                .onFailure { error -> runOnUiThread { contentLoadError = error.message ?: "资料库无法打开" } }
        }.start()
    }
}

@Composable
private fun ContentLibraryState(error: String?) {
    Surface(modifier = Modifier.fillMaxSize(), color = XuanPaper) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize().padding(32.dp)) {
            Text(
                text = error ?: "正在打开资料库…",
                color = if (error == null) InkSoft else Vermilion,
                fontFamily = FontFamily.Serif,
                fontSize = 17.sp,
            )
        }
    }
}

private data class AppSection(
    val label: String,
    val iconRes: Int? = null,
    val vectorIcon: ImageVector? = null,
    val activeColor: Color,
)

private val BottomNavigationIconSize = 24.dp

private val appSections = listOf(
    AppSection(label = "岁月", iconRes = R.drawable.nav_timeline_woodblock, activeColor = Vermilion),
    AppSection(label = "人物", iconRes = R.drawable.nav_people_woodblock, activeColor = Vermilion),
    AppSection(label = "天下", vectorIcon = Icons.Outlined.Public, activeColor = Vermilion),
    AppSection(label = "我的", vectorIcon = Icons.Outlined.Person, activeColor = Vermilion),
)

@Composable
private fun TwoCapitalsApp(repository: MingRepository) {
    var selectedSection by rememberSaveable { mutableIntStateOf(0) }
    var searchOpen by rememberSaveable { mutableStateOf(false) }
    var searchDestination by remember { mutableStateOf<SearchDestination?>(null) }
    var focusPerson by remember { mutableStateOf<String?>(null) }
    var personReturnSection by rememberSaveable { mutableStateOf<Int?>(null) }
    // 事件可从人物、机构或典章详情进入；返回时回到原详情与其原有滚动位置。
    var eventReturnSection by rememberSaveable { mutableStateOf<Int?>(null) }
    val sectionStateHolder = rememberSaveableStateHolder()

    fun openEventFrom(section: Int, eventId: String) {
        val eventReign = repository.reigns().firstOrNull { reign ->
            reign.events.any { event -> event.id == eventId }
        }
        val event = eventReign?.events?.firstOrNull { it.id == eventId }
        if (eventReign != null && event != null) {
            eventReturnSection = section
            searchDestination = SearchDestination(
                sectionIndex = 0,
                reignTitle = eventReign.title,
                year = event.year,
                eventId = event.id,
            )
            selectedSection = 0
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = XuanPaper,
        bottomBar = {
            if (!searchOpen) {
                MingBottomBar(
                    selectedSection = selectedSection,
                    onSectionSelected = { destination ->
                        if (destination != selectedSection) {
                            focusPerson = null
                            personReturnSection = null
                            eventReturnSection = null
                            searchDestination = null
                        }
                        selectedSection = destination
                    },
                )
            }
        },
    ) { innerPadding ->
        if (searchOpen) {
            GlobalSearchScreen(
                repository = repository,
                onDismiss = { searchOpen = false },
                onNavigate = { destination ->
                    searchOpen = false
                    if (destination.personName != null) personReturnSection = selectedSection
                    else personReturnSection = null
                    selectedSection = destination.sectionIndex
                    focusPerson = destination.personName
                    searchDestination = destination.takeIf { it.reignTitle != null || it.worldSection != null }
                },
            )
        } else {
            sectionStateHolder.SaveableStateProvider("section-$selectedSection") {
                when (selectedSection) {
                    0 -> TimelineScreen(
                        repository = repository,
                        contentPadding = innerPadding,
                        searchDestination = searchDestination,
                        onSearchDestinationConsumed = { searchDestination = null },
                        onSearch = { searchOpen = true },
                        onOpenPerson = { name ->
                            personReturnSection = selectedSection
                            focusPerson = name
                            selectedSection = 1
                        },
                        returnToPrevious = eventReturnSection != null,
                        onReturnToPrevious = {
                            val destination = eventReturnSection
                            eventReturnSection = null
                            if (destination != null) selectedSection = destination
                        },
                    )
                    1 -> PeopleScreen(
                        repository = repository,
                        contentPadding = innerPadding,
                        focusPerson = focusPerson,
                        onFocusConsumed = { focusPerson = null },
                        onProfileExit = {
                            personReturnSection?.let { origin ->
                                personReturnSection = null
                                selectedSection = origin
                            }
                        },
                        onOpenEvent = { eventId -> openEventFrom(section = 1, eventId = eventId) },
                        onSearch = { searchOpen = true },
                    )
                    2 -> WorldScreen(
                        repository = repository,
                        contentPadding = innerPadding,
                        searchDestination = searchDestination,
                        onSearchDestinationConsumed = { searchDestination = null },
                        onSearch = { searchOpen = true },
                        onOpenPerson = { name ->
                            personReturnSection = selectedSection
                            focusPerson = name
                            selectedSection = 1
                        },
                        onOpenEvent = { eventId -> openEventFrom(section = 2, eventId = eventId) },
                    )
                    else -> ProfileScreen(innerPadding, onSearch = { searchOpen = true })
                }
            }
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
                    // 四项一律占用同一个 24dp 画框，选中仅改变颜色，绝不改变大小或位置。
                    Box(
                        modifier = Modifier.size(BottomNavigationIconSize),
                        contentAlignment = Alignment.Center,
                    ) {
                        when {
                            section.vectorIcon != null -> Icon(
                                imageVector = section.vectorIcon,
                                contentDescription = section.label,
                                modifier = Modifier.fillMaxSize(),
                                tint = tint,
                            )

                            section.iconRes != null -> Image(
                                painter = painterResource(section.iconRes),
                                contentDescription = section.label,
                                modifier = Modifier.fillMaxSize(),
                                contentScale = ContentScale.Inside,
                                colorFilter = ColorFilter.tint(tint),
                            )
                        }
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
