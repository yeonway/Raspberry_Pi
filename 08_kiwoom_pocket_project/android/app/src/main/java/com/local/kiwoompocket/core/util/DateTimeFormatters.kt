package com.local.kiwoompocket.core.util

object DateTimeFormatters {
    fun compactDate(value: String?): String {
        if (value.isNullOrBlank() || value.length < 8) return "-"
        return "${value.substring(0, 4)}-${value.substring(4, 6)}-${value.substring(6, 8)}"
    }
}
