package com.local.kiwoompocket.core.database

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface StockDao {
    @Query("SELECT * FROM watch_stocks ORDER BY createdAt DESC")
    fun observeWatchStocks(): Flow<List<WatchStockEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertWatchStock(entity: WatchStockEntity)

    @Query("DELETE FROM watch_stocks WHERE code = :code")
    suspend fun deleteWatchStock(code: String)

    @Query("SELECT * FROM recent_stocks ORDER BY updatedAt DESC LIMIT 20")
    fun observeRecentStocks(): Flow<List<RecentStockEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertRecentStock(entity: RecentStockEntity)
}
