package com.ljyss.ui.people

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CutCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.PersonOutline
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ljyss.R
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.ui.theme.Brass
import com.ljyss.ui.theme.Ink
import com.ljyss.ui.theme.InkSoft
import com.ljyss.ui.theme.LineGold
import com.ljyss.ui.theme.PaperLight
import com.ljyss.ui.theme.PaperShade
import com.ljyss.ui.theme.Vermilion

internal val PersonCardPortraitWidth = 116.dp
internal val PersonCardPortraitHeight = 160.dp

@Composable
internal fun PersonCard(
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
                        text = person.displayName,
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
                        text = "  ${person.title}  ",
                        color = Vermilion,
                        fontFamily = FontFamily.Serif,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    HorizontalDivider(modifier = Modifier.width(26.dp), color = Brass)
                }
                Text(person.reign, color = InkSoft, fontFamily = FontFamily.Serif, fontSize = 14.sp)
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
internal fun PersonPortrait(person: HistoricalPerson) {
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
