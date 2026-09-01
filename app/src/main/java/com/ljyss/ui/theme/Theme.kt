package com.ljyss.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val MingLightColors = lightColorScheme(
    primary = Vermilion,
    onPrimary = PaperLight,
    primaryContainer = Color(0xFFF0D7CC),
    onPrimaryContainer = VermilionDark,
    secondary = Celadon,
    onSecondary = PaperLight,
    secondaryContainer = CeladonLight,
    onSecondaryContainer = Celadon,
    tertiary = Indigo,
    onTertiary = PaperLight,
    background = XuanPaper,
    onBackground = Ink,
    surface = PaperLight,
    onSurface = Ink,
    surfaceVariant = PaperShade,
    onSurfaceVariant = InkSoft,
    outline = LineGold,
)

private val MingDarkColors = darkColorScheme(
    primary = Color(0xFFE09A84),
    onPrimary = Color(0xFF401007),
    secondary = Color(0xFF9BC8B6),
    onSecondary = Color(0xFF08362A),
    tertiary = Color(0xFFA9C7E2),
    onTertiary = Color(0xFF0D2D42),
    background = Color(0xFF1E201B),
    onBackground = Color(0xFFF2E8D1),
    surface = Color(0xFF282922),
    onSurface = Color(0xFFF2E8D1),
    surfaceVariant = Color(0xFF48483B),
    onSurfaceVariant = Color(0xFFD0C7B1),
    outline = Color(0xFF978A6B),
)

@Composable
fun MingAppTheme(
    darkTheme: Boolean = false,
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) MingDarkColors else MingLightColors,
        typography = Typography,
        content = content,
    )
}
