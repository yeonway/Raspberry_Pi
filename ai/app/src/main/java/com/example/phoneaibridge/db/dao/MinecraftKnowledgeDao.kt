package com.example.phoneaibridge.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.example.phoneaibridge.db.entity.MinecraftKnowledgeEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MinecraftKnowledgeDao {
    @Query("SELECT * FROM minecraft_knowledge ORDER BY updated_at DESC") fun observeAll(): Flow<List<MinecraftKnowledgeEntity>>
    @Insert suspend fun insert(entity: MinecraftKnowledgeEntity): Long
    @Query("DELETE FROM minecraft_knowledge WHERE id = :id") suspend fun deleteById(id: Long)
}
