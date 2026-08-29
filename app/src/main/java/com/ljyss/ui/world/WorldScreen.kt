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
internal fun WorldScreen(repository: MingRepository, contentPadding: PaddingValues) {
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
