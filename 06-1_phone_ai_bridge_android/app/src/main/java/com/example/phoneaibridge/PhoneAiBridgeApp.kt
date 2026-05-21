package com.example.phoneaibridge

import android.app.Application
import com.example.phoneaibridge.ai.AiEngine
import com.example.phoneaibridge.ai.PhoneAiEngine
import com.example.phoneaibridge.db.AppDatabase
import com.example.phoneaibridge.model.ModelStore
import com.example.phoneaibridge.rag.KeywordRagSearcher
import com.example.phoneaibridge.repository.AiRequestLogRepository
import com.example.phoneaibridge.repository.CoordinateRepository
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
    lateinit var modelStore: ModelStore
    lateinit var database: AppDatabase
    lateinit var playerMemoryRepository: PlayerMemoryRepository
    lateinit var knowledgeRepository: KnowledgeRepository
    lateinit var coordinateRepository: CoordinateRepository
    lateinit var aiRequestLogRepository: AiRequestLogRepository
    lateinit var ragSearcher: KeywordRagSearcher
    lateinit var aiEngine: AiEngine
    lateinit var apiRoutes: ApiRoutes
    lateinit var localHttpServer: LocalHttpServer

    fun init(app: Application) {
        settings = SettingsStore(app)
        modelStore = ModelStore(app)
        database = AppDatabase.create(app)
        playerMemoryRepository = PlayerMemoryRepository(database.playerMemoryDao())
        knowledgeRepository = KnowledgeRepository(database.minecraftKnowledgeDao(), database.ragChunkDao())
        coordinateRepository = CoordinateRepository(database.minecraftCoordinateDao())
        aiRequestLogRepository = AiRequestLogRepository(database.aiRequestLogDao())
        ragSearcher = KeywordRagSearcher(database.ragChunkDao())
        aiEngine = PhoneAiEngine(modelStore, settings)
        apiRoutes = ApiRoutes(settings, playerMemoryRepository, knowledgeRepository, coordinateRepository, aiRequestLogRepository, ragSearcher, aiEngine)
        localHttpServer = LocalHttpServer(settings, apiRoutes)
    }
}
