package com.example.phoneaibridge.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "ai_request_logs")
data class AiRequestLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "player_uuid") val playerUuid: String? = null,
    @ColumnInfo(name = "player_name") val playerName: String? = null,
    val message: String,
    @ColumnInfo(name = "retrieved_context") val retrievedContext: String = "",
    val answer: String = "",
    @ColumnInfo(name = "latency_ms") val latencyMs: Long = 0,
    val ok: Boolean = true,
    @ColumnInfo(name = "error_message") val errorMessage: String? = null,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
)
