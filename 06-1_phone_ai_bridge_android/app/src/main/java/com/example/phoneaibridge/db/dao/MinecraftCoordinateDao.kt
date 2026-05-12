package com.example.phoneaibridge.db.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MinecraftCoordinateDao {
    @Query("SELECT * FROM minecraft_coordinates ORDER BY updated_at DESC")
    fun observeAll(): Flow<List<MinecraftCoordinateEntity>>

    @Query("SELECT * FROM minecraft_coordinates ORDER BY updated_at DESC")
    suspend fun getAll(): List<MinecraftCoordinateEntity>

    @Query("SELECT * FROM minecraft_coordinates WHERE id = :id LIMIT 1")
    suspend fun findById(id: String): MinecraftCoordinateEntity?

    @Query("SELECT COUNT(*) FROM minecraft_coordinates")
    suspend fun count(): Int

    @Upsert
    suspend fun upsert(entity: MinecraftCoordinateEntity)

    @Query("DELETE FROM minecraft_coordinates WHERE id = :id")
    suspend fun deleteById(id: String)
}
