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
import com.ljyss.ui.profile.ProfileScreen
import com.ljyss.ui.world.WorldScreen
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

@Preview(showBackground = true, heightDp = 840)
@Composable
private fun TwoCapitalsAppPreview() {
    两京一十三省Theme {
        TwoCapitalsApp(repository = SeedMingRepository)
    }
}
