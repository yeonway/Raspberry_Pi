package com.example.phoneaibridge.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface AiRequestLogDao {
    @Query("SELECT * FROM ai_request_logs ORDER BY created_at DESC LIMIT :limit") fun observeRecent(limit: Int = 50): Flow<List<AiRequestLogEntity>>
    @Query("SELECT * FROM ai_request_logs ORDER BY created_at DESC LIMIT :limit") suspend fun recent(limit: Int = 50): List<AiRequestLogEntity>
    @Insert suspend fun insert(entity: AiRequestLogEntity): Long
    @Query("SELECT COUNT(*) FROM ai_request_logs") fun observeCount(): Flow<Int>
    @Query("SELECT error_message FROM ai_request_logs WHERE ok = 0 AND error_message IS NOT NULL ORDER BY created_at DESC LIMIT 1") fun observeLatestError(): Flow<String?>
}
