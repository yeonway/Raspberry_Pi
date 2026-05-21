package com.example.phoneaibridge.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(
    tableName = "minecraft_coordinates",
    indices = [
        Index(value = ["name"]),
        Index(value = ["world"]),
        Index(value = ["updated_at"]),
    ],
)
data class MinecraftCoordinateEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val name: String,
    val aliases: String = "",
    val world: String = "overworld",
    val x: Double,
    val y: Double? = null,
    val z: Double,
    val tags: String = "",
    val description: String? = null,
    @ColumnInfo(name = "created_by") val createdBy: String? = null,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = System.currentTimeMillis(),
)
