package com.example.phoneaibridge.repository

import com.example.phoneaibridge.db.dao.AiRequestLogDao
import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import kotlinx.coroutines.flow.Flow

class AiRequestLogRepository(private val dao: AiRequestLogDao) {
    fun observeRecent(limit: Int = 50): Flow<List<AiRequestLogEntity>> = dao.observeRecent(limit)
    fun observeCount(): Flow<Int> = dao.observeCount()
    fun observeLatestError(): Flow<String?> = dao.observeLatestError()
    suspend fun recent(limit: Int = 50): List<AiRequestLogEntity> = dao.recent(limit)
    suspend fun insert(entity: AiRequestLogEntity): Long = dao.insert(entity)
}
