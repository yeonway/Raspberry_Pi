package com.example.phoneaibridge

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class SavedCoordinate(
    val id: String,
    val name: String,
    val world: String,
    val x: Double,
    val y: Double?,
    val z: Double,
    val description: String,
    val createdBy: String,
    val tags: List<String>,
) {
    fun toJson(): JSONObject {
        val json = JSONObject()
            .put("id", id)
            .put("name", name)
            .put("world", world)
            .put("x", x)
            .put("z", z)
            .put("description", description)
            .put("created_by", createdBy)
            .put("tags", JSONArray(tags))
        if (y != null) json.put("y", y)
        return json
    }

    fun searchText(): String {
        return listOf(id, name, world, description, createdBy, tags.joinToString(" "))
            .joinToString(" ")
            .lowercase()
    }

    companion object {
        fun fromJson(json: JSONObject): SavedCoordinate {
            val tagsJson = json.optJSONArray("tags") ?: JSONArray()
            val tags = (0 until tagsJson.length()).map { tagsJson.optString(it) }.filter { it.isNotBlank() }
            return SavedCoordinate(
                id = json.optString("id").ifBlank { json.optString("name", "coordinate") },
                name = json.optString("name").ifBlank { json.optString("id", "coordinate") },
                world = json.optString("world", "overworld"),
                x = json.optDouble("x", 0.0),
                y = if (json.has("y") && !json.isNull("y")) json.optDouble("y") else null,
                z = json.optDouble("z", 0.0),
                description = json.optString("description").ifBlank { json.optString("note") },
                createdBy = json.optString("created_by").ifBlank { json.optString("owner") },
                tags = tags,
            )
        }
    }
}

object CoordinateStore {
    private const val PREFS_NAME = "phone_local_bridge"
    private const val KEY_COORDINATES = "coordinates_json"

    private val lock = Any()
    private var loaded = false
    private val coordinates = linkedMapOf<String, SavedCoordinate>()

    fun upsert(context: Context, json: JSONObject): SavedCoordinate {
        synchronized(lock) {
            ensureLoaded(context)
            val coordinate = SavedCoordinate.fromJson(json)
            coordinates[coordinate.id] = coordinate
            saveLocked(context)
            return coordinate
        }
    }

    fun count(context: Context): Int {
        synchronized(lock) {
            ensureLoaded(context)
            return coordinates.size
        }
    }

    fun list(context: Context): List<SavedCoordinate> {
        synchronized(lock) {
            ensureLoaded(context)
            return coordinates.values.toList()
        }
    }

    private fun ensureLoaded(context: Context) {
        if (loaded) return
        coordinates.clear()
        val raw = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_COORDINATES, "[]")
            .orEmpty()
        val array = runCatching { JSONArray(raw) }.getOrElse { JSONArray() }
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            val coordinate = runCatching { SavedCoordinate.fromJson(item) }.getOrNull() ?: continue
            coordinates[coordinate.id] = coordinate
        }
        loaded = true
    }

    private fun saveLocked(context: Context) {
        val array = JSONArray()
        coordinates.values.forEach { array.put(it.toJson()) }
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_COORDINATES, array.toString())
            .apply()
    }
}
