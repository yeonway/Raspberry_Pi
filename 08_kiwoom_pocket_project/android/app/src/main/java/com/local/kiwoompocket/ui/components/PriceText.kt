package com.local.kiwoompocket.ui.components

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import com.local.kiwoompocket.core.util.NumberFormatters
import com.local.kiwoompocket.ui.theme.FallBlue
import com.local.kiwoompocket.ui.theme.NeutralGray
import com.local.kiwoompocket.ui.theme.RiseRed

@Composable
fun PriceText(value: Long, changeRate: Double? = null, prefix: String = "") {
    val color = when {
        changeRate == null -> MaterialTheme.colorScheme.onSurface
        changeRate > 0.0 -> RiseRed
        changeRate < 0.0 -> FallBlue
        else -> NeutralGray
    }
    Text(
        text = "$prefix${NumberFormatters.won(value)}${changeRate?.let { " ${NumberFormatters.percent(it)}" } ?: ""}",
        color = color,
        fontWeight = FontWeight.SemiBold,
    )
}

fun rateColor(rate: Double): Color = when {
    rate > 0.0 -> RiseRed
    rate < 0.0 -> FallBlue
    else -> NeutralGray
}
