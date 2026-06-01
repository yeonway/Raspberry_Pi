package com.local.kiwoompocket.core.database

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "recent_stocks")
data class RecentStockEntity(
    @PrimaryKey val code: String,
    val name: String,
    val price: Long,
    val changePrice: Long,
    val changeRate: Double,
    val volume: Long,
    val updatedAt: Long = System.currentTimeMillis(),
)
