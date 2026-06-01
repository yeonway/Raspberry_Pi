package com.local.kiwoompocket.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = BrandGreen,
    secondary = Color(0xFF455A64),
    tertiary = Color(0xFF7B5E2E),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF62D6A5),
    secondary = Color(0xFFB0BEC5),
    tertiary = Color(0xFFE3C17A),
)

@Composable
fun KiwoomPocketTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}
