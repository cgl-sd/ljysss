package com.ljyss.ui.world

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.MingRepository
import com.ljyss.R
import com.ljyss.data.model.Institution
import com.ljyss.data.model.SpecialItem
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.components.Seal
import com.ljyss.ui.components.SourceNote
import com.ljyss.ui.search.SearchDestination
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Celadon
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion
import com.ljyss.ui.theme.XuanPaper

@Composable
internal fun WorldScreen(
    repository: MingRepository,
    contentPadding: PaddingValues,
    searchDestination: SearchDestination? = null,
    onSearchDestinationConsumed: () -> Unit = {},
    onSearch: () -> Unit = {},
) {
    var worldSection by rememberSaveable { mutableStateOf(WorldSection.MAP) }
    val institutions = remember(repository) { repository.institutions() }
    val specials = remember(repository) { repository.specialItems() }
    val institutionGroups = remember(institutions) {
        institutionCategoryDefinitions.filter { group -> institutions.any { it.category in group.categories } }
    }
    val relicGroups = remember(specials) {
        specialCategoryDefinitions.filter { group -> specials.any { it.category in group.categories } }
    }
    var selectedInstitutionGroup by rememberSaveable { mutableStateOf("中央政务") }
    var selectedRelicGroup by rememberSaveable { mutableStateOf("制度法令") }
    LaunchedEffect(searchDestination) {
        val destination = searchDestination ?: return@LaunchedEffect
        destination.worldSection?.let { label ->
            WorldSection.entries.firstOrNull { it.label == label }?.let { worldSection = it }
        }
        destination.worldCategory?.let { category ->
            institutionGroups.firstOrNull { category in it.categories }?.let { selectedInstitutionGroup = it.label }
            relicGroups.firstOrNull { category in it.categories }?.let { selectedRelicGroup = it.label }
        }
        onSearchDestinationConsumed()
    }

    MingList(contentPadding) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                MingMasthead(onSearch)
                OrnamentalTitle("天下")
                WorldSectionRail(
                    selected = worldSection,
                    onSelected = { worldSection = it },
                )
            }
        }
        when (worldSection) {
            WorldSection.MAP -> {
                item {
                    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        AtlasMapPlate(modifier = Modifier.fillMaxWidth())
                    }
                }
            }
            WorldSection.INSTITUTIONS -> {
                item {
                    WorldCategoryRail(institutionGroups, selectedInstitutionGroup) { selectedInstitutionGroup = it }
                }
                val selectedGroup = institutionGroups.firstOrNull { it.label == selectedInstitutionGroup } ?: institutionGroups.firstOrNull()
                val filteredInstitutions = selectedGroup?.let { group -> institutions.filter { it.category in group.categories } }.orEmpty()
                items(filteredInstitutions, key = { it.id }) { institution ->
                    InstitutionCard(institution)
                }
            }
            WorldSection.RELICS -> {
                if (specials.isEmpty()) {
                    item { SourceNote("典章科普内容将在内容服务载入后显示。") }
                } else {
                    item {
                        WorldCategoryRail(relicGroups, selectedRelicGroup) { selectedRelicGroup = it }
                    }
                    val selectedGroup = relicGroups.firstOrNull { it.label == selectedRelicGroup } ?: relicGroups.firstOrNull()
                    val filteredSpecials = selectedGroup?.let { group -> specials.filter { it.category in group.categories } }.orEmpty()
                    items(filteredSpecials, key = { it.id }) { item ->
                        SpecialItemCard(item)
                    }
                }
            }
        }
    }
}

/** 紧凑舆图版：完整地图、花纹题签与两张说明卡须在同一屏连续可见。 */
@Composable
private fun AtlasMapPlate(modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = CutCornerShape(11.dp),
        color = PaperLight,
        border = BorderStroke(1.4.dp, LineGold),
    ) {
        Column(modifier = Modifier.padding(5.dp), verticalArrangement = Arrangement.spacedBy(0.dp)) {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = CutCornerShape(7.dp),
                color = PaperShade.copy(alpha = 0.42f),
                border = BorderStroke(1.dp, Brass.copy(alpha = 0.65f)),
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(692f / 820f)
                        .padding(4.dp)
                        .clip(CutCornerShape(4.dp))
                        .background(XuanPaper),
                ) {
                    Image(
                        painter = painterResource(R.drawable.world_atlas_wide),
                        contentDescription = "明代两京十三省地图",
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Fit,
                    )
                }
            }
            AtlasCaption()
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 7.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                AtlasInfoCard(
                    title = "两京",
                    detail = "北京\n南京",
                    illustration = R.drawable.atlas_two_capitals_palace,
                    modifier = Modifier.weight(1f),
                )
                AtlasInfoCard(
                    title = "十三省",
                    detail = null,
                    illustration = R.drawable.atlas_thirteen_provinces_landscape,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun AtlasCaption() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .padding(horizontal = 8.dp, vertical = 3.dp),
        contentAlignment = Alignment.Center,
    ) {
        Image(
            painter = painterResource(R.drawable.atlas_title_plaque),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.FillWidth,
        )
        Text(
            "明代两京一十三省舆图",
            color = Ink,
            fontFamily = FontFamily.Serif,
            fontSize = 15.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun AtlasInfoCard(title: String, detail: String?, illustration: Int, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.height(72.dp),
        shape = CutCornerShape(6.dp),
        color = PaperShade.copy(alpha = 0.42f),
        border = BorderStroke(1.dp, LineGold.copy(alpha = 0.8f)),
    ) {
        Box(modifier = Modifier.fillMaxSize().padding(horizontal = 10.dp, vertical = 8.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                detail?.let {
                    Text(it, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp, lineHeight = 15.sp)
                }
            }
            Image(
                painter = painterResource(illustration),
                contentDescription = null,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .width(72.dp)
                    .height(30.dp),
                contentScale = ContentScale.Fit,
            )
        }
    }
}

/** 天下页的三个栏目：舆图 / 机构 / 典章。 */
private enum class WorldSection(val label: String) {
    MAP("舆图"),
    INSTITUTIONS("机构"),
    RELICS("典章"),
}

/** 机构按办事主体分，典章按制度、物件与场所分；同一实体只保留一个主归属。 */
private data class WorldCategoryGroup(val label: String, val categories: Set<String>)

private val institutionCategoryDefinitions = listOf(
    WorldCategoryGroup("中央政务", setOf("中央政务")),
    WorldCategoryGroup("监察司法", setOf("监察司法")),
    WorldCategoryGroup("军事卫所", setOf("军事卫所")),
    WorldCategoryGroup("内廷宦官", setOf("内廷宦官")),
    WorldCategoryGroup("皇帝亲军", setOf("皇帝亲军")),
    WorldCategoryGroup("皇族事务", setOf("皇族事务")),
    WorldCategoryGroup("地方治理", setOf("地方治理")),
    WorldCategoryGroup("教育礼制", setOf("教育礼制")),
)

private val specialCategoryDefinitions = listOf(
    WorldCategoryGroup("制度法令", setOf("制度")),
    WorldCategoryGroup("器物文书", setOf("器物")),
    WorldCategoryGroup("礼俗生活", setOf("习俗")),
    WorldCategoryGroup("宫阙陵寝", setOf("宫阙", "陵寝")),
    WorldCategoryGroup("史事专题", setOf("专题")),
)

@Composable
private fun WorldCategoryRail(
    groups: List<WorldCategoryGroup>,
    selected: String,
    onSelected: (String) -> Unit,
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
        items(groups, key = { it.label }) { group ->
            val active = group.label == selected
            Surface(
                modifier = Modifier.clip(CutCornerShape(5.dp)).clickable { onSelected(group.label) },
                shape = CutCornerShape(5.dp),
                color = if (active) Vermilion else PaperLight,
                border = BorderStroke(1.dp, if (active) Vermilion else LineGold),
            ) {
                Text(
                    group.label,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    color = if (active) PaperLight else Ink,
                    fontFamily = FontFamily.Serif,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
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
