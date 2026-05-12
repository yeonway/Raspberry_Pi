package com.example.phoneaibridge.server

import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import com.example.phoneaibridge.rag.RagResult
import org.json.JSONArray
import org.json.JSONObject

fun jsonError(message: String): String = JSONObject().put("ok", false).put("error", message).toString()
fun jsonError(code: String, message: String): String = JSONObject()
    .put("ok", false)
    .put("error", code)
    .put("message", message)
    .toString()
fun PlayerMemoryEntity.toJson(): JSONObject = JSONObject().put("player_uuid", playerUuid).put("player_name", playerName).put("summary", summary).put("current_goal", currentGoal).put("last_location_text", lastLocationText).put("recent_question", recentQuestion).put("confidence", confidence).put("created_at", createdAt).put("updated_at", updatedAt)
fun MinecraftCoordinateEntity.toJson(): JSONObject = JSONObject()
    .put("id", id)
    .put("name", name)
    .put("aliases", aliases.splitToJsonArray())
    .put("world", world)
    .put("x", x)
    .put("y", y ?: JSONObject.NULL)
    .put("z", z)
    .put("tags", tags.splitToJsonArray())
    .put("description", description ?: JSONObject.NULL)
    .put("created_by", createdBy ?: JSONObject.NULL)
    .put("created_at", createdAt)
    .put("updated_at", updatedAt)
fun RagResult.toJson(): JSONObject = JSONObject().put("title", title).put("chunk_text", chunkText).put("score", score).put("tags", tags)
fun AiRequestLogEntity.toJson(): JSONObject = JSONObject().put("id", id).put("player_uuid", playerUuid).put("player_name", playerName).put("message", message).put("retrieved_context", retrievedContext).put("answer", answer).put("latency_ms", latencyMs).put("ok", ok).put("error_message", errorMessage).put("created_at", createdAt)
fun Iterable<JSONObject>.toJsonArray(): JSONArray = JSONArray().also { arr -> forEach { arr.put(it) } }
private fun String.splitToJsonArray(): JSONArray = JSONArray().also { array ->
    split(',', '\n', '|').map { it.trim() }.filter { it.isNotBlank() }.forEach { array.put(it) }
}
