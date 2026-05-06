package com.example.phoneaibridge.repository

import com.example.phoneaibridge.db.dao.MinecraftKnowledgeDao
import com.example.phoneaibridge.db.dao.RagChunkDao
import com.example.phoneaibridge.db.entity.MinecraftKnowledgeEntity
import com.example.phoneaibridge.db.entity.RagChunkEntity
import kotlinx.coroutines.flow.Flow

class KnowledgeRepository(private val knowledgeDao: MinecraftKnowledgeDao, private val chunkDao: RagChunkDao) {
    fun observeAll(): Flow<List<MinecraftKnowledgeEntity>> = knowledgeDao.observeAll()
    suspend fun ingest(title: String, content: String, sourceType: String, tags: String): Long {
        val now = System.currentTimeMillis()
        val id = knowledgeDao.insert(MinecraftKnowledgeEntity(title = title, content = content, sourceType = sourceType, tags = tags, createdAt = now, updatedAt = now))
        val chunks = chunkContent(content).map { text -> RagChunkEntity(knowledgeId = id, title = title, chunkText = text, embeddingTextOrVectorStub = null, tags = tags, createdAt = now) }
        chunkDao.insertAll(chunks.ifEmpty { listOf(RagChunkEntity(knowledgeId = id, title = title, chunkText = content, tags = tags, createdAt = now)) })
        return id
    }
    suspend fun delete(id: Long) { chunkDao.deleteByKnowledgeId(id); knowledgeDao.deleteById(id) }
    private fun chunkContent(content: String, size: Int = 480): List<String> = content.chunked(size).map { it.trim() }.filter { it.isNotBlank() }
}
