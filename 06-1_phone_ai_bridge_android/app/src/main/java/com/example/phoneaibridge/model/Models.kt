package com.example.phoneaibridge.model

data class AskRequest(val playerUuid: String?, val playerName: String?, val message: String, val serverContext: String = "", val coordinateContext: String = "", val sparkContext: String = "", val maxTokens: Int = 160)
data class AskResponse(val ok: Boolean, val answer: String, val usedMemory: Boolean, val usedRag: Boolean, val latencyMs: Long)
data class HealthResponse(val ok: Boolean, val serverRunning: Boolean, val modelLoaded: Boolean, val engine: String, val dbReady: Boolean, val port: Int, val time: String)
data class PlayerMemoryDto(val playerName: String, val summary: String, val currentGoal: String?, val lastLocationText: String?, val recentQuestion: String?, val confidence: Double)
data class KnowledgeDto(val title: String, val content: String, val sourceType: String = "manual", val tags: String = "")
data class ApiErrorResponse(val ok: Boolean = false, val error: String)
