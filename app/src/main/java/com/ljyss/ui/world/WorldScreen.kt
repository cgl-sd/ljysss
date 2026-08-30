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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Layers
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
    var modernOverlayEnabled by rememberSaveable { mutableStateOf(false) }
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
        item { MingMasthead(onSearch) }
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
                    AtlasMapPlate(
                        modernOverlayEnabled = modernOverlayEnabled,
                        onLayerToggle = { modernOverlayEnabled = !modernOverlayEnabled },
                    )
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

/** 保持原始舆图不变，只以纸本衬框和相连题签把地图纳入页面版式。 */
@Composable
private fun AtlasMapPlate(modernOverlayEnabled: Boolean, onLayerToggle: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = CutCornerShape(9.dp),
        color = PaperShade.copy(alpha = 0.44f),
        border = BorderStroke(1.25.dp, LineGold),
    ) {
        Column(modifier = Modifier.padding(6.dp), verticalArrangement = Arrangement.spacedBy(0.dp)) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(448.dp)
                    .clip(CutCornerShape(6.dp))
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
                        modifier = Modifier.fillMaxSize().alpha(0.68f),
                        contentScale = ContentScale.Crop,
                        alignment = Alignment.Center,
                    )
                }
                Surface(
                    modifier = Modifier.align(Alignment.BottomEnd).padding(11.dp),
                    shape = RoundedCornerShape(50),
                    color = PaperLight.copy(alpha = 0.94f),
                    border = BorderStroke(1.dp, Brass.copy(alpha = 0.55f)),
                ) {
                    IconButton(onClick = onLayerToggle, modifier = Modifier.size(42.dp)) {
                        Icon(Icons.Outlined.Layers, contentDescription = "切换现代区划图层", tint = Ink)
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 11.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                AtlasFact("两京", "北京 · 南京", Modifier.weight(1f))
                AtlasFact("十三省", "明代地方建置", Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun AtlasFact(title: String, detail: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(title, color = Vermilion, fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Text(detail, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 12.sp)
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
