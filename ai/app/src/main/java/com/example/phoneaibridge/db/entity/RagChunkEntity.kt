package com.example.phoneaibridge.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "rag_chunks")
data class RagChunkEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "knowledge_id") val knowledgeId: Long,
    val title: String,
    @ColumnInfo(name = "chunk_text") val chunkText: String,
    @ColumnInfo(name = "embedding_text_or_vector_stub") val embeddingTextOrVectorStub: String? = null,
    val tags: String = "",
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
)
