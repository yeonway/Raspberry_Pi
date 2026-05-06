package com.example.phoneaibridge.server

import com.example.phoneaibridge.ai.AiEngine
import com.example.phoneaibridge.ai.AiPromptBuilder
import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import com.example.phoneaibridge.network.NetworkInfoProvider
import com.example.phoneaibridge.rag.RagSearcher
import com.example.phoneaibridge.repository.AiRequestLogRepository
import com.example.phoneaibridge.repository.KnowledgeRepository
import com.example.phoneaibridge.repository.PlayerMemoryRepository
import com.example.phoneaibridge.settings.SettingsStore
import org.json.JSONArray
import org.json.JSONObject
import java.time.OffsetDateTime

class ApiRoutes(
    private val settingsStore: SettingsStore,
    private val memoryRepository: PlayerMemoryRepository,
    private val knowledgeRepository: KnowledgeRepository,
    private val logRepository: AiRequestLogRepository,
    private val ragSearcher: RagSearcher,
    private val aiEngine: AiEngine,
) {
    suspend fun handle(method: String, rawPath: String, headers: Map<String, String>, body: String, remoteIp: String?): HttpResponse {
        val path = rawPath.substringBefore('?')
        if (!AuthMiddleware.isAuthorized(path, headers, remoteIp, settingsStore.read())) return HttpResponse(401, jsonError("unauthorized"))
        return try {
            when {
                method == "GET" && path == "/health" -> health()
                method == "POST" && path == "/api/ask" -> ask(JSONObject(body))
                method == "GET" && path.startsWith("/api/player/") && path.endsWith("/memory") -> getMemory(path)
                method == "POST" && path.startsWith("/api/player/") && path.endsWith("/memory") -> postMemory(path, JSONObject(body))
                method == "POST" && path == "/api/rag/ingest" -> ingest(JSONObject(body))
                method == "POST" && path == "/api/rag/search" -> search(JSONObject(body))
                method == "GET" && path == "/api/logs" -> logs(rawPath)
                else -> HttpResponse(404, jsonError("not found"))
            }
        } catch (e: org.json.JSONException) {
            HttpResponse(400, jsonError("invalid json: ${e.message}"))
        } catch (e: Exception) {
            logRepository.insert(AiRequestLogEntity(message = path, ok = false, errorMessage = e.message ?: "unknown error"))
            HttpResponse(500, jsonError("internal error"))
        }
    }

    private suspend fun health(): HttpResponse {
        val settings = settingsStore.read()
        val networkInfo = NetworkInfoProvider.getNetworkInfo(settings.port)
        return HttpResponse(
            200,
            JSONObject()
                .put("ok", true)
                .put("server_running", ServerState.snapshot.value.running)
                .put("model_loaded", aiEngine.isLoaded())
                .put("engine", aiEngine::class.java.simpleName)
                .put("db_ready", true)
                .put("port", settings.port)
                .put("time", OffsetDateTime.now().toString())
                .put("primary_ip", networkInfo.primaryIp ?: JSONObject.NULL)
                .put("local_ips", JSONArray(networkInfo.localIps))
                .put("api_base_url", networkInfo.apiBaseUrl ?: JSONObject.NULL)
                .put("health_url", networkInfo.healthUrl ?: JSONObject.NULL)
                .toString(),
        )
    }

    private suspend fun ask(json: JSONObject): HttpResponse {
        val start = System.currentTimeMillis()
        val playerUuid = json.optString("player_uuid", null)
        val playerName = json.optString("player_name", null)
        val message = json.getString("message")
        val memory = playerUuid?.takeIf { it.isNotBlank() }?.let { memoryRepository.findByUuid(it) }
        val rag = ragSearcher.search(message, 5)
        val retrieved = rag.joinToString("\n") { "${it.title}: ${it.chunkText}" }
        val prompt = AiPromptBuilder.build(memory, json.optString("coordinate_context"), json.optString("server_context"), json.optString("spark_context"), rag, message)
        val answer = aiEngine.generate(prompt, json.optInt("max_tokens", 160))
        val latency = System.currentTimeMillis() - start
        logRepository.insert(AiRequestLogEntity(playerUuid = playerUuid, playerName = playerName, message = message, retrievedContext = retrieved, answer = answer, latencyMs = latency, ok = true))
        return HttpResponse(200, JSONObject().put("ok", true).put("answer", answer).put("used_memory", memory != null).put("used_rag", rag.isNotEmpty()).put("latency_ms", latency).toString())
    }

    private suspend fun getMemory(path: String): HttpResponse {
        val uuid = path.removePrefix("/api/player/").removeSuffix("/memory")
        val memory = memoryRepository.findByUuid(uuid) ?: return HttpResponse(404, jsonError("memory not found"))
        return HttpResponse(200, JSONObject().put("ok", true).put("memory", memory.toJson()).toString())
    }

    private suspend fun postMemory(path: String, json: JSONObject): HttpResponse {
        val uuid = path.removePrefix("/api/player/").removeSuffix("/memory")
        val now = System.currentTimeMillis()
        val existing = memoryRepository.findByUuid(uuid)
        val entity = PlayerMemoryEntity(id = existing?.id ?: 0, playerUuid = uuid, playerName = json.getString("player_name"), summary = json.getString("summary"), currentGoal = json.optString("current_goal", null), lastLocationText = json.optString("last_location_text", null), recentQuestion = json.optString("recent_question", null), confidence = json.optDouble("confidence", 0.7), createdAt = existing?.createdAt ?: now, updatedAt = now)
        memoryRepository.save(entity)
        return HttpResponse(200, JSONObject().put("ok", true).put("memory", entity.toJson()).toString())
    }

    private suspend fun ingest(json: JSONObject): HttpResponse {
        val id = knowledgeRepository.ingest(json.getString("title"), json.getString("content"), json.optString("source_type", "manual"), json.optString("tags", ""))
        return HttpResponse(200, JSONObject().put("ok", true).put("knowledge_id", id).toString())
    }

    private suspend fun search(json: JSONObject): HttpResponse {
        val results = ragSearcher.search(json.getString("query"), json.optInt("limit", 5))
        return HttpResponse(200, JSONObject().put("ok", true).put("results", results.map { it.toJson() }.toJsonArray()).toString())
    }

    private suspend fun logs(rawPath: String): HttpResponse {
        val limit = rawPath.substringAfter("limit=", "50").substringBefore('&').toIntOrNull() ?: 50
        return HttpResponse(200, JSONObject().put("ok", true).put("logs", logRepository.recent(limit).map { it.toJson() }.toJsonArray()).toString())
    }
}

data class HttpResponse(val code: Int, val body: String, val contentType: String = "application/json; charset=utf-8")
