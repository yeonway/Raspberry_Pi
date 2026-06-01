package com.local.kiwoompocket.core.database

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "watch_stocks")
data class WatchStockEntity(
    @PrimaryKey val code: String,
    val name: String,
    val market: String = "KRX",
    val memo: String = "",
    val createdAt: Long = System.currentTimeMillis(),
)
