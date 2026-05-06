package com.example.phoneaibridge.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.example.phoneaibridge.db.entity.RagChunkEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface RagChunkDao {
    @Query("SELECT * FROM rag_chunks ORDER BY created_at DESC") fun observeAll(): Flow<List<RagChunkEntity>>
    @Query("SELECT * FROM rag_chunks") suspend fun getAll(): List<RagChunkEntity>
    @Insert suspend fun insertAll(chunks: List<RagChunkEntity>)
    @Query("DELETE FROM rag_chunks WHERE knowledge_id = :knowledgeId") suspend fun deleteByKnowledgeId(knowledgeId: Long)
}
