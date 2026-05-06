package com.example.phoneaibridge.db.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface PlayerMemoryDao {
    @Query("SELECT * FROM player_memory ORDER BY updated_at DESC") fun observeAll(): Flow<List<PlayerMemoryEntity>>
    @Query("SELECT * FROM player_memory WHERE player_uuid = :uuid LIMIT 1") suspend fun findByUuid(uuid: String): PlayerMemoryEntity?
    @Query("SELECT * FROM player_memory WHERE player_uuid LIKE '%' || :query || '%' OR player_name LIKE '%' || :query || '%' ORDER BY updated_at DESC") fun search(query: String): Flow<List<PlayerMemoryEntity>>
    @Upsert suspend fun upsert(entity: PlayerMemoryEntity): Long
}
