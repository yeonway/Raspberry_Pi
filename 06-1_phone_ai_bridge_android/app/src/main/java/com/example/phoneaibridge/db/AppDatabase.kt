package com.example.phoneaibridge.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.example.phoneaibridge.db.dao.AiRequestLogDao
import com.example.phoneaibridge.db.dao.MinecraftKnowledgeDao
import com.example.phoneaibridge.db.dao.PlayerMemoryDao
import com.example.phoneaibridge.db.dao.RagChunkDao
import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import com.example.phoneaibridge.db.entity.MinecraftKnowledgeEntity
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import com.example.phoneaibridge.db.entity.RagChunkEntity

@Database(
    entities = [PlayerMemoryEntity::class, MinecraftKnowledgeEntity::class, RagChunkEntity::class, AiRequestLogEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun playerMemoryDao(): PlayerMemoryDao
    abstract fun minecraftKnowledgeDao(): MinecraftKnowledgeDao
    abstract fun ragChunkDao(): RagChunkDao
    abstract fun aiRequestLogDao(): AiRequestLogDao

    companion object {
        fun create(context: Context): AppDatabase = Room.databaseBuilder(context, AppDatabase::class.java, "phone_ai_bridge.db").build()
    }
}
