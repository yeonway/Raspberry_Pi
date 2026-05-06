package com.example.phoneaibridge

import android.app.Application
import com.example.phoneaibridge.ai.MockAiEngine
import com.example.phoneaibridge.db.AppDatabase
import com.example.phoneaibridge.rag.KeywordRagSearcher
import com.example.phoneaibridge.repository.AiRequestLogRepository
import com.example.phoneaibridge.repository.KnowledgeRepository
import com.example.phoneaibridge.repository.PlayerMemoryRepository
import com.example.phoneaibridge.server.ApiRoutes
import com.example.phoneaibridge.server.LocalHttpServer
import com.example.phoneaibridge.settings.SettingsStore

class PhoneAiBridgeApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Graph.init(this)
    }
}

object Graph {
    lateinit var settings: SettingsStore
    lateinit var database: AppDatabase
    lateinit var playerMemoryRepository: PlayerMemoryRepository
    lateinit var knowledgeRepository: KnowledgeRepository
    lateinit var aiRequestLogRepository: AiRequestLogRepository
    lateinit var ragSearcher: KeywordRagSearcher
    lateinit var aiEngine: MockAiEngine
    lateinit var apiRoutes: ApiRoutes
    lateinit var localHttpServer: LocalHttpServer

    fun init(app: Application) {
        settings = SettingsStore(app)
        database = AppDatabase.create(app)
        playerMemoryRepository = PlayerMemoryRepository(database.playerMemoryDao())
        knowledgeRepository = KnowledgeRepository(database.minecraftKnowledgeDao(), database.ragChunkDao())
        aiRequestLogRepository = AiRequestLogRepository(database.aiRequestLogDao())
        ragSearcher = KeywordRagSearcher(database.ragChunkDao())
        aiEngine = MockAiEngine()
        apiRoutes = ApiRoutes(settings, playerMemoryRepository, knowledgeRepository, aiRequestLogRepository, ragSearcher, aiEngine)
        localHttpServer = LocalHttpServer(settings, apiRoutes)
    }
}
