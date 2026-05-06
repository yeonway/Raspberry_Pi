package com.example.phoneaibridge.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "player_memory", indices = [Index(value = ["player_uuid"], unique = true)])
data class PlayerMemoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "player_uuid") val playerUuid: String,
    @ColumnInfo(name = "player_name") val playerName: String,
    val summary: String,
    @ColumnInfo(name = "current_goal") val currentGoal: String? = null,
    @ColumnInfo(name = "last_location_text") val lastLocationText: String? = null,
    @ColumnInfo(name = "recent_question") val recentQuestion: String? = null,
    val confidence: Double = 0.7,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = System.currentTimeMillis(),
)
