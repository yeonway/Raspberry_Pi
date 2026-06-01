package com.local.kiwoompocket.core.database

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [WatchStockEntity::class, RecentStockEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun stockDao(): StockDao
}
