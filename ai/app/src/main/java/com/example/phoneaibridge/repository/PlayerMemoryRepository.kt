package com.example.phoneaibridge.repository

import com.example.phoneaibridge.db.dao.PlayerMemoryDao
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import kotlinx.coroutines.flow.Flow

class PlayerMemoryRepository(private val dao: PlayerMemoryDao) {
    fun observeAll(): Flow<List<PlayerMemoryEntity>> = dao.observeAll()
    fun search(query: String): Flow<List<PlayerMemoryEntity>> = dao.search(query)
    suspend fun findByUuid(uuid: String): PlayerMemoryEntity? = dao.findByUuid(uuid)
    suspend fun save(entity: PlayerMemoryEntity): Long = dao.upsert(entity.copy(updatedAt = System.currentTimeMillis()))
}
