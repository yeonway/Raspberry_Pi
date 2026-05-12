package com.example.phoneaibridge.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.phoneaibridge.db.dao.AiRequestLogDao
import com.example.phoneaibridge.db.dao.MinecraftCoordinateDao
import com.example.phoneaibridge.db.dao.MinecraftKnowledgeDao
import com.example.phoneaibridge.db.dao.PlayerMemoryDao
import com.example.phoneaibridge.db.dao.RagChunkDao
import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import com.example.phoneaibridge.db.entity.MinecraftKnowledgeEntity
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import com.example.phoneaibridge.db.entity.RagChunkEntity

@Database(
    entities = [
        PlayerMemoryEntity::class,
        MinecraftKnowledgeEntity::class,
        RagChunkEntity::class,
        AiRequestLogEntity::class,
        MinecraftCoordinateEntity::class,
    ],
    version = 2,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun playerMemoryDao(): PlayerMemoryDao
    abstract fun minecraftKnowledgeDao(): MinecraftKnowledgeDao
    abstract fun ragChunkDao(): RagChunkDao
    abstract fun aiRequestLogDao(): AiRequestLogDao
    abstract fun minecraftCoordinateDao(): MinecraftCoordinateDao

    companion object {
        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS `minecraft_coordinates` (
                        `id` TEXT NOT NULL,
                        `name` TEXT NOT NULL,
                        `aliases` TEXT NOT NULL,
                        `world` TEXT NOT NULL,
                        `x` REAL NOT NULL,
                        `y` REAL,
                        `z` REAL NOT NULL,
                        `tags` TEXT NOT NULL,
                        `description` TEXT,
                        `created_by` TEXT,
                        `created_at` INTEGER NOT NULL,
                        `updated_at` INTEGER NOT NULL,
                        PRIMARY KEY(`id`)
                    )
                    """.trimIndent(),
                )
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_minecraft_coordinates_name` ON `minecraft_coordinates` (`name`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_minecraft_coordinates_world` ON `minecraft_coordinates` (`world`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_minecraft_coordinates_updated_at` ON `minecraft_coordinates` (`updated_at`)")
            }
        }

        fun create(context: Context): AppDatabase = Room.databaseBuilder(context, AppDatabase::class.java, "phone_ai_bridge.db")
            .addMigrations(MIGRATION_1_2)
            .build()
    }
}
