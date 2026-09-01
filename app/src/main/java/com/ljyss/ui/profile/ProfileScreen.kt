package com.ljyss.ui.profile

import android.annotation.SuppressLint
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.MenuBook
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.data.MingRepository
import com.ljyss.data.model.TravelGuide
import com.ljyss.ui.components.MingArticleSection
import com.ljyss.ui.components.MingList
import com.ljyss.ui.components.MingMasthead
import com.ljyss.ui.components.OrnamentalTitle
import com.ljyss.ui.components.Seal
import com.ljyss.ui.search.SearchDestination
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion

private val GuideCardImageWidth = 112.dp
private val GuideCardImageHeight = 94.dp
private val GuideDetailImageHeight = 220.dp

/** “我的”页的知识目录。内容来自随 APK 发布的 SQLite，不依赖网络。 */
@Composable
internal fun ProfileScreen(
    repository: MingRepository,
    contentPadding: PaddingValues,
    searchDestination: SearchDestination? = null,
    onSearchDestinationConsumed: () -> Unit = {},
    onSearch: () -> Unit = {},
) {
    val guides = remember(repository) { repository.travelGuides() }
    var selectedGuideId by rememberSaveable { mutableStateOf<String?>(null) }
    val listState = rememberLazyListState()
    LaunchedEffect(searchDestination) {
        val guideId = searchDestination?.guideId ?: return@LaunchedEffect
        if (guides.any { it.id == guideId }) selectedGuideId = guideId
        onSearchDestinationConsumed()
    }
    val selectedGuide = guides.firstOrNull { it.id == selectedGuideId }
    BackHandler(enabled = selectedGuide != null) { selectedGuideId = null }
    if (selectedGuide != null) {
        GuideDetailScreen(selectedGuide, contentPadding)
        return
    }

    MingList(contentPadding, state = listState) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                MingMasthead(onSearch)
                OrnamentalTitle("我的")
            }
        }
        item { TravelGuideSectionTitle() }
        items(guides, key = { it.id }) { guide ->
            TravelGuideCard(guide, onOpen = { selectedGuideId = guide.id })
        }
    }
}

@Composable
private fun TravelGuideSectionTitle() {
    Surface(
        shape = CutCornerShape(5.dp),
        color = PaperShade.copy(alpha = 0.48f),
        border = BorderStroke(1.dp, LineGold),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 11.dp, vertical = 7.dp),
            horizontalArrangement = Arrangement.spacedBy(7.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.MenuBook, contentDescription = null, tint = Vermilion, modifier = Modifier.height(19.dp))
            Text("穿越手册", color = Ink, fontFamily = FontFamily.Serif, fontSize = 17.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun TravelGuideCard(guide: TravelGuide, onOpen: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().heightIn(min = 118.dp).clickable(onClick = onOpen),
        shape = CutCornerShape(9.dp),
        border = BorderStroke(1.25.dp, LineGold),
        colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = .96f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            GuideAssetImage(
                asset = guide.imageAsset,
                contentDescription = "${guide.title}插绘",
                modifier = Modifier.width(GuideCardImageWidth).height(GuideCardImageHeight).clip(CutCornerShape(5.dp)),
                contentScale = ContentScale.Crop,
            )
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(guide.title, color = Ink, modifier = Modifier.weight(1f), fontFamily = FontFamily.Serif, fontSize = 18.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Seal(guide.category)
                }
                Text(guide.description, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp, lineHeight = 19.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(guide.subtitle, color = Brass, fontFamily = FontFamily.Serif, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

@Composable
private fun GuideDetailScreen(guide: TravelGuide, contentPadding: PaddingValues) {
    MingList(contentPadding) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = CutCornerShape(10.dp),
                border = BorderStroke(1.3.dp, LineGold),
                colors = CardDefaults.cardColors(containerColor = PaperLight.copy(alpha = .96f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(guide.title, color = Ink, fontFamily = FontFamily.Serif, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                    Text(guide.category + "｜" + guide.subtitle, color = Brass, fontFamily = FontFamily.Serif, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    GuideAssetImage(
                        asset = guide.imageAsset,
                        contentDescription = "${guide.title}专题插绘",
                        modifier = Modifier.fillMaxWidth().height(GuideDetailImageHeight).clip(CutCornerShape(7.dp)),
                        contentScale = ContentScale.Crop,
                    )
                    val sections = guide.sections.sortedBy { it.position }.filter { it.content.isNotBlank() }
                    if (sections.isEmpty()) MingArticleSection("概览", guide.description)
                    else sections.forEach { section -> MingArticleSection(section.title, section.content) }
                }
            }
        }
    }
}

@Composable
@SuppressLint("DiscouragedApi", "LocalContextResourcesRead")
private fun GuideAssetImage(asset: String, contentDescription: String, modifier: Modifier, contentScale: ContentScale) {
    val context = LocalContext.current
    val resource = remember(asset, context.packageName) {
        context.resources.getIdentifier(asset, "drawable", context.packageName).takeIf { it != 0 }
    }
    Box(modifier = modifier.background(PaperShade.copy(alpha = .52f)), contentAlignment = Alignment.Center) {
        if (resource != null) {
            Image(painterResource(resource), contentDescription, modifier = Modifier.fillMaxSize(), contentScale = contentScale)
        } else {
            Icon(Icons.Outlined.MenuBook, contentDescription = null, tint = Brass, modifier = Modifier.height(34.dp))
        }
    }
}
