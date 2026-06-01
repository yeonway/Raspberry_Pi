package com.local.kiwoompocket.core.util

import java.text.NumberFormat
import java.util.Locale

object NumberFormatters {
    private val number = NumberFormat.getNumberInstance(Locale.KOREA)

    fun won(value: Long): String = "${number.format(value)}원"
    fun quantity(value: Long): String = number.format(value)
    fun percent(value: Double): String = String.format(Locale.KOREA, "%+.2f%%", value)
}
