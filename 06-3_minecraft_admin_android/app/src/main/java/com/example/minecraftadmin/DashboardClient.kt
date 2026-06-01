package com.example.minecraftadmin

import android.content.Context
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

object DashboardClient {
    private const val PREFS = "minecraft_admin"
    private const val KEY_URL = "dashboard_url"
    private const val KEY_TOKEN = "event_token"
    private const val KEY_MC_ADDRESS = "minecraft_address"

    const val DEFAULT_URL = "https://op.dcout.site"
    const val DEFAULT_TOKEN = ""
    const val DEFAULT_MC_ADDRESS = "op.dcout.site:25565"

    fun dashboardUrl(context: Context): String {
        return prefs(context).getString(KEY_URL, DEFAULT_URL).orEmpty().ifBlank { DEFAULT_URL }
    }

    fun eventToken(context: Context): String {
        return prefs(context).getString(KEY_TOKEN, DEFAULT_TOKEN).orEmpty().ifBlank { DEFAULT_TOKEN }
    }

    fun minecraftAddress(context: Context): String {
        return prefs(context).getString(KEY_MC_ADDRESS, DEFAULT_MC_ADDRESS).orEmpty().ifBlank { DEFAULT_MC_ADDRESS }
    }

    fun save(context: Context, url: String, token: String, minecraftAddress: String) {
        prefs(context).edit()
            .putString(KEY_URL, url.trim().trimEnd('/').ifBlank { DEFAULT_URL })
            .putString(KEY_TOKEN, token.trim())
            .putString(KEY_MC_ADDRESS, minecraftAddress.trim().ifBlank { DEFAULT_MC_ADDRESS })
            .apply()
    }

    fun get(context: Context, path: String): JSONObject {
        return request(context, "GET", path, null)
    }

    fun post(context: Context, path: String, payload: JSONObject = JSONObject()): JSONObject {
        return request(context, "POST", path, payload)
    }

    private fun request(context: Context, method: String, path: String, payload: JSONObject?): JSONObject {
        val base = dashboardUrl(context).trimEnd('/')
        val token = eventToken(context)
        require(token.isNotBlank()) { "Event token is not configured." }
        val normalizedPath = if (path.startsWith("/")) path else "/$path"
        val body = payload?.toString()?.toByteArray(StandardCharsets.UTF_8)
        val connection = (URL(base + normalizedPath).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8000
            readTimeout = 15000
            setRequestProperty("Accept", "application/json")
            setRequestProperty("X-Event-Token", token)
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Content-Length", body.size.toString())
            }
        }

        try {
            if (body != null) {
                connection.outputStream.use { it.write(body) }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.use { input ->
                BufferedReader(InputStreamReader(input, StandardCharsets.UTF_8)).readText()
            }.orEmpty()
            if (status !in 200..299) {
                throw IllegalStateException("HTTP $status $response")
            }
            return if (response.isBlank()) JSONObject() else JSONObject(response)
        } finally {
            connection.disconnect()
        }
    }

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
