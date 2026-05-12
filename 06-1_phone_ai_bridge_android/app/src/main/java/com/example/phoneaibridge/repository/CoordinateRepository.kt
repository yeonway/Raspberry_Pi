package com.example.phoneaibridge.repository

import com.example.phoneaibridge.coordinate.CoordinateRagSearcher
import com.example.phoneaibridge.coordinate.CoordinateSearchResult
import com.example.phoneaibridge.db.dao.MinecraftCoordinateDao
import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import kotlinx.coroutines.flow.Flow

class CoordinateRepository(private val dao: MinecraftCoordinateDao) {
    fun observeAll(): Flow<List<MinecraftCoordinateEntity>> = dao.observeAll()

    suspend fun all(): List<MinecraftCoordinateEntity> = dao.getAll()

    suspend fun count(): Int = dao.count()

    suspend fun save(entity: MinecraftCoordinateEntity): MinecraftCoordinateEntity {
        val now = System.currentTimeMillis()
        val existing = dao.findById(entity.id)
        val saved = entity.copy(
            createdAt = existing?.createdAt ?: entity.createdAt,
            updatedAt = now,
        )
        dao.upsert(saved)
        return saved
    }

    suspend fun delete(id: String) {
        dao.deleteById(id)
    }

    suspend fun search(query: String, coordinateContext: String = "", limit: Int = 8): List<CoordinateSearchResult> {
        return CoordinateRagSearcher.search(query, coordinateContext, dao.getAll(), limit)
    }

    fun isCoordinateQuery(query: String): Boolean = CoordinateRagSearcher.isCoordinateQuery(query)
}
