package com.example.phoneaibridge.server

import com.example.phoneaibridge.ai.AiBusyException
import com.example.phoneaibridge.ai.AiEngine
import com.example.phoneaibridge.ai.AiPromptBuilder
import com.example.phoneaibridge.ai.ModelNotReadyException
import com.example.phoneaibridge.coordinate.CoordinatePromptFormatter
import com.example.phoneaibridge.coordinate.CoordinateRagSearcher
import com.example.phoneaibridge.coordinate.CoordinateSearchResult
import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import com.example.phoneaibridge.network.NetworkInfoProvider
import com.example.phoneaibridge.rag.RagSearcher
import com.example.phoneaibridge.repository.AiRequestLogRepository
import com.example.phoneaibridge.repository.CoordinateRepository
import com.example.phoneaibridge.repository.KnowledgeRepository
import com.example.phoneaibridge.repository.PlayerMemoryRepository
import com.example.phoneaibridge.settings.AppSettings
import com.example.phoneaibridge.settings.SettingsStore
import org.json.JSONArray
import org.json.JSONObject
import java.time.OffsetDateTime
import java.util.UUID

class ApiRoutes(
    private val settingsStore: SettingsStore,
    private val memoryRepository: PlayerMemoryRepository,
    private val knowledgeRepository: KnowledgeRepository,
    private val coordinateRepository: CoordinateRepository,
    private val logRepository: AiRequestLogRepository,
    private val ragSearcher: RagSearcher,
    private val aiEngine: AiEngine,
) {
    suspend fun handle(method: String, rawPath: String, headers: Map<String, String>, body: String, remoteIp: String?): HttpResponse {
        val path = rawPath.substringBefore('?')
        if (!AuthMiddleware.isAuthorized(path, headers, remoteIp, settingsStore.read())) {
            return HttpResponse(401, jsonError("UNAUTHORIZED", "API Token이 올바르지 않습니다."))
        }
        return try {
            when {
                method == "GET" && path == "/health" -> health()
                method == "POST" && path == "/api/ask" -> ask(JSONObject(body))
                method == "GET" && path.startsWith("/api/player/") && path.endsWith("/memory") -> getMemory(path)
                method == "POST" && path.startsWith("/api/player/") && path.endsWith("/memory") -> postMemory(path, JSONObject(body))
                method == "POST" && path == "/api/rag/ingest" -> ingest(JSONObject(body))
                method == "POST" && path == "/api/rag/search" -> search(JSONObject(body))
                method == "GET" && path == "/api/coordinates" -> listCoordinates()
                method == "POST" && path == "/api/coordinates" -> saveCoordinate(JSONObject(body))
                method == "POST" && path == "/api/coordinates/search" -> searchCoordinates(JSONObject(body))
                method == "DELETE" && path.startsWith("/api/coordinates/") -> deleteCoordinate(path)
                method == "GET" && path == "/api/logs" -> logs(rawPath)
                else -> HttpResponse(404, jsonError("not found"))
            }
        } catch (e: org.json.JSONException) {
            HttpResponse(400, jsonError("INVALID_JSON", "요청 JSON이 올바르지 않습니다."))
        } catch (e: Exception) {
            logRepository.insert(AiRequestLogEntity(message = path, ok = false, errorMessage = e.message ?: "unknown error"))
            HttpResponse(500, jsonError("INTERNAL_ERROR", "알 수 없는 오류가 발생했습니다."))
        }
    }

    private suspend fun health(): HttpResponse {
        val settings = settingsStore.read()
        val networkInfo = NetworkInfoProvider.getNetworkInfo(settings.port)
        val model = com.example.phoneaibridge.Graph.modelStore.current()
        val loaded = aiEngine.isLoaded()
        return HttpResponse(
            200,
            JSONObject()
                .put("ok", true)
                .put("server", if (ServerState.snapshot.value.running) "running" else "stopped")
                .put("server_running", ServerState.snapshot.value.running)
                .put("modelSelected", model.selected)
                .put("modelLoaded", loaded)
                .put("modelName", model.name)
                .put("busy", model.busy)
                .put("model_loaded", loaded)
                .put("model_selected", model.selected)
                .put("model_name", model.name)
                .put("model_size_bytes", model.sizeBytes)
                .put("model_status", model.lastMessage)
                .put("engine", aiEngine::class.java.simpleName)
                .put("db_ready", true)
                .put("coordinate_count", coordinateRepository.count())
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
        val playerUuid = json.optString("player_uuid").takeIf { it.isNotBlank() }
        val playerName = json.optString("player_name").takeIf { it.isNotBlank() }
        val message = json.getString("message")
        val settings = settingsStore.read()
        val systemPrompt = json.optionalSystemPrompt()
            ?: settings.systemPrompt.takeIf { it.isNotBlank() }
            ?: AppSettings.DEFAULT_SYSTEM_PROMPT
        val coordinateContext = json.optString("coordinate_context")
        val memory = playerUuid?.takeIf { it.isNotBlank() }?.let { memoryRepository.findByUuid(it) }
        val coordinateQuery = coordinateRepository.isCoordinateQuery(message)
        val coordinateMatches = coordinateRepository.search(message, coordinateContext, json.optInt("coordinate_limit", 8))

        if (coordinateQuery && coordinateMatches.isEmpty()) {
            val answer = if (coordinateRepository.count() == 0) {
                "아직 저장된 좌표가 없어요."
            } else {
                "저장된 좌표에서 해당 위치를 찾지 못했어요."
            }
            val latency = System.currentTimeMillis() - start
            logRepository.insert(
                AiRequestLogEntity(
                    playerUuid = playerUuid,
                    playerName = playerName,
                    message = message,
                    retrievedContext = "Coordinate RAG: no match",
                    answer = answer,
                    latencyMs = latency,
                    ok = true,
                ),
            )
            return HttpResponse(
                200,
                JSONObject()
                    .put("ok", true)
                    .put("answer", answer)
                    .put("used_memory", memory != null)
                    .put("used_rag", false)
                    .put("used_coordinate_rag", false)
                    .put("coordinate_matches", JSONArray())
                    .put("latency_ms", latency)
                    .toString(),
            )
        }

        val rag = ragSearcher.search(message, 5)
        val coordinateRagContext = CoordinatePromptFormatter.format(coordinateMatches, coordinateQuery)
        val retrieved = listOf(
            "Coordinate RAG:\n$coordinateRagContext",
            "General RAG:\n${rag.joinToString("\n") { "${it.title}: ${it.chunkText}" }}",
        ).joinToString("\n\n")
        val prompt = AiPromptBuilder.build(
            systemPrompt,
            memory,
            coordinateContext,
            coordinateRagContext,
            json.optString("server_context"),
            json.optString("spark_context"),
            rag,
            message,
        )
        val answer = try {
            aiEngine.generate(prompt, json.optInt("max_tokens", 160))
        } catch (e: ModelNotReadyException) {
            logGenerationError(playerUuid, playerName, message, retrieved, start, e)
            return HttpResponse(409, jsonError("MODEL_NOT_LOADED", "모델이 선택되지 않았습니다."))
        } catch (e: AiBusyException) {
            logGenerationError(playerUuid, playerName, message, retrieved, start, e)
            return HttpResponse(429, jsonError("AI_BUSY", "AI가 다른 요청을 처리 중입니다."))
        } catch (e: Exception) {
            logGenerationError(playerUuid, playerName, message, retrieved, start, e)
            return HttpResponse(500, jsonError("GENERATION_FAILED", "AI 응답 생성에 실패했습니다."))
        }

        val latency = System.currentTimeMillis() - start
        logRepository.insert(AiRequestLogEntity(playerUuid = playerUuid, playerName = playerName, message = message, retrievedContext = retrieved, answer = answer, latencyMs = latency, ok = true))
        return HttpResponse(
            200,
            JSONObject()
                .put("ok", true)
                .put("answer", answer)
                .put("used_memory", memory != null)
                .put("used_rag", rag.isNotEmpty() || coordinateMatches.isNotEmpty())
                .put("used_coordinate_rag", coordinateMatches.isNotEmpty())
                .put("coordinate_matches", coordinateMatches.map { it.toJson() }.toJsonArray())
                .put("latency_ms", latency)
                .toString(),
        )
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
        val entity = PlayerMemoryEntity(
            id = existing?.id ?: 0,
            playerUuid = uuid,
            playerName = json.getString("player_name"),
            summary = json.getString("summary"),
            currentGoal = json.optString("current_goal").takeIf { it.isNotBlank() },
            lastLocationText = json.optString("last_location_text").takeIf { it.isNotBlank() },
            recentQuestion = json.optString("recent_question").takeIf { it.isNotBlank() },
            confidence = json.optDouble("confidence", 0.7),
            createdAt = existing?.createdAt ?: now,
            updatedAt = now,
        )
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

    private suspend fun listCoordinates(): HttpResponse {
        return HttpResponse(200, JSONObject().put("ok", true).put("coordinates", coordinateRepository.all().map { it.toJson() }.toJsonArray()).toString())
    }

    private suspend fun saveCoordinate(json: JSONObject): HttpResponse {
        val name = json.getString("name").trim()
        if (name.isBlank()) return HttpResponse(400, jsonError("coordinate name is required"))
        val entity = MinecraftCoordinateEntity(
            id = json.optString("id").takeIf { it.isNotBlank() } ?: UUID.randomUUID().toString(),
            name = name,
            aliases = CoordinateRagSearcher.encodeList(json.optStringList("aliases")),
            world = CoordinateRagSearcher.normalizeWorld(json.optString("world", json.optString("dimension", "overworld"))),
            x = json.getDouble("x"),
            y = if (json.has("y") && !json.isNull("y")) json.getDouble("y") else null,
            z = json.getDouble("z"),
            tags = CoordinateRagSearcher.encodeList(json.optStringList("tags")),
            description = json.optString("description").takeIf { it.isNotBlank() } ?: json.optString("memo").takeIf { it.isNotBlank() },
            createdBy = json.optString("created_by").takeIf { it.isNotBlank() } ?: json.optString("player_name").takeIf { it.isNotBlank() },
        )
        val saved = coordinateRepository.save(entity)
        return HttpResponse(200, JSONObject().put("ok", true).put("coordinate", saved.toJson()).toString())
    }

    private suspend fun searchCoordinates(json: JSONObject): HttpResponse {
        val results = coordinateRepository.search(
            query = json.getString("query"),
            coordinateContext = json.optString("coordinate_context"),
            limit = json.optInt("limit", 8),
        )
        return HttpResponse(200, JSONObject().put("ok", true).put("results", results.map { it.toJson() }.toJsonArray()).toString())
    }

    private suspend fun deleteCoordinate(path: String): HttpResponse {
        val id = path.removePrefix("/api/coordinates/").trim()
        if (id.isBlank()) return HttpResponse(400, jsonError("coordinate id is required"))
        coordinateRepository.delete(id)
        return HttpResponse(200, JSONObject().put("ok", true).put("deleted", id).toString())
    }

    private suspend fun logs(rawPath: String): HttpResponse {
        val limit = rawPath.substringAfter("limit=", "50").substringBefore('&').toIntOrNull() ?: 50
        return HttpResponse(200, JSONObject().put("ok", true).put("logs", logRepository.recent(limit).map { it.toJson() }.toJsonArray()).toString())
    }

    private suspend fun logGenerationError(
        playerUuid: String?,
        playerName: String?,
        message: String,
        retrieved: String,
        start: Long,
        error: Exception,
    ) {
        logRepository.insert(
            AiRequestLogEntity(
                playerUuid = playerUuid,
                playerName = playerName,
                message = message,
                retrievedContext = retrieved,
                latencyMs = System.currentTimeMillis() - start,
                ok = false,
                errorMessage = error.message,
            ),
        )
    }

    private fun JSONObject.optStringList(key: String): List<String> {
        if (!has(key) || isNull(key)) return emptyList()
        return when (val value = opt(key)) {
            is JSONArray -> (0 until value.length()).mapNotNull { value.optString(it).takeIf { item -> item.isNotBlank() } }
            is String -> CoordinateRagSearcher.splitList(value)
            else -> emptyList()
        }
    }

    private fun JSONObject.optionalSystemPrompt(): String? {
        return optString("systemPrompt").takeIf { it.isNotBlank() }
            ?: optString("system_prompt").takeIf { it.isNotBlank() }
    }

    private fun CoordinateSearchResult.toJson(): JSONObject = JSONObject()
        .put("coordinate", coordinate.toJson())
        .put("score", score)
        .put("reason", reason)
        .put("distance_blocks", distanceBlocks ?: JSONObject.NULL)
}

data class HttpResponse(val code: Int, val body: String, val contentType: String = "application/json; charset=utf-8")
