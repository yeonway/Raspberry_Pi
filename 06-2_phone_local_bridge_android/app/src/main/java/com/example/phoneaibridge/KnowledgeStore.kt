package com.example.phoneaibridge

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

data class SavedKnowledge(
    val id: String,
    val title: String,
    val content: String,
    val tags: List<String>,
) {
    fun toJson(): JSONObject {
        return JSONObject()
            .put("id", id)
            .put("title", title)
            .put("content", content)
            .put("tags", JSONArray(tags))
    }

    fun searchText(): String {
        return listOf(title, content, tags.joinToString(" "))
            .joinToString(" ")
            .lowercase()
    }

    fun toPromptText(): String {
        val tagText = if (tags.isEmpty()) "" else " #${tags.joinToString(" #")}"
        return "$title$tagText: $content"
    }

    companion object {
        fun fromJson(json: JSONObject): SavedKnowledge {
            val tagsJson = json.optJSONArray("tags") ?: JSONArray()
            val tags = (0 until tagsJson.length())
                .map { tagsJson.optString(it).trim() }
                .filter { it.isNotBlank() }
            val title = json.optString("title").ifBlank { json.optString("name") }.ifBlank { "지식" }
            val content = json.optString("content").ifBlank { json.optString("text") }
            return SavedKnowledge(
                id = json.optString("id").ifBlank { UUID.randomUUID().toString() },
                title = title,
                content = content,
                tags = tags,
            )
        }
    }
}

object KnowledgeStore {
    private const val PREFS_NAME = "phone_local_bridge"
    private const val KEY_KNOWLEDGE = "knowledge_json"

    private val lock = Any()
    private var loaded = false
    private val items = linkedMapOf<String, SavedKnowledge>()

    fun upsert(context: Context, json: JSONObject): SavedKnowledge {
        synchronized(lock) {
            ensureLoaded(context)
            val item = SavedKnowledge.fromJson(json)
            require(item.content.isNotBlank()) { "지식 내용이 비어 있습니다" }
            items[item.id] = item
            saveLocked(context)
            return item
        }
    }

    fun count(context: Context): Int {
        synchronized(lock) {
            ensureLoaded(context)
            return items.size
        }
    }

    fun list(context: Context): List<SavedKnowledge> {
        synchronized(lock) {
            ensureLoaded(context)
            return items.values.toList()
        }
    }

    fun search(context: Context, query: String, limit: Int = 6): List<SavedKnowledge> {
        val words = query
            .lowercase()
            .split(Regex("\\s+"))
            .map { it.trim { char -> !char.isLetterOrDigit() && char != '_' && char != '-' } }
            .filter { it.length >= 2 }

        synchronized(lock) {
            ensureLoaded(context)
            if (words.isEmpty()) return items.values.take(limit)
            return items.values
                .map { item ->
                    val text = item.searchText()
                    val score = words.count { word -> text.contains(word) }
                    item to score
                }
                .filter { (_, score) -> score > 0 }
                .sortedByDescending { (_, score) -> score }
                .map { (item, _) -> item }
                .take(limit)
        }
    }

    private fun ensureLoaded(context: Context) {
        if (loaded) return
        items.clear()
        val raw = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_KNOWLEDGE, "[]")
            .orEmpty()
        val array = runCatching { JSONArray(raw) }.getOrElse { JSONArray() }
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            val knowledge = runCatching { SavedKnowledge.fromJson(item) }.getOrNull() ?: continue
            if (knowledge.content.isNotBlank()) {
                items[knowledge.id] = knowledge
            }
        }
        loaded = true
    }

    private fun saveLocked(context: Context) {
        val array = JSONArray()
        items.values.forEach { array.put(it.toJson()) }
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_KNOWLEDGE, array.toString())
            .apply()
    }
}
