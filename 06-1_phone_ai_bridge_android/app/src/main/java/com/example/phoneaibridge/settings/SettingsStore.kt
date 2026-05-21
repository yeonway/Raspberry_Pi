package com.example.phoneaibridge.settings

import android.content.Context
import java.security.SecureRandom

class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("phone_ai_bridge_settings", Context.MODE_PRIVATE)
    fun read(): AppSettings {
        var token = prefs.getString(KEY_TOKEN, null)
        if (token.isNullOrBlank()) {
            token = generateToken()
            prefs.edit().putString(KEY_TOKEN, token).apply()
        }
        return AppSettings(
            port = prefs.getInt(KEY_PORT, 8765),
            apiToken = token,
            modelPath = prefs.getString(KEY_MODEL_PATH, AppSettings.DEFAULT_GGUF_MODEL_PATH).orEmpty(),
            allowedRaspberryPiIp = prefs.getString(KEY_ALLOWED_IP, "").orEmpty(),
            nCtx = prefs.getInt(KEY_N_CTX, 2048),
            nThreads = prefs.getInt(KEY_N_THREADS, 4),
            maxTokens = prefs.getInt(KEY_MAX_TOKENS, 256),
            temperature = prefs.getFloat(KEY_TEMPERATURE, 0.7f),
            autoStartServer = prefs.getBoolean(KEY_AUTO_START, false),
            autoLoadModel = prefs.getBoolean(KEY_AUTO_LOAD, false),
            keepAliveInBackground = prefs.getBoolean(KEY_KEEP_ALIVE, true),
            systemPrompt = prefs.getString(KEY_SYSTEM_PROMPT, AppSettings.DEFAULT_SYSTEM_PROMPT).orEmpty(),
        )
    }
    fun save(settings: AppSettings) {
        prefs.edit()
            .putInt(KEY_PORT, settings.port)
            .putString(KEY_TOKEN, settings.apiToken)
            .putString(KEY_MODEL_PATH, settings.modelPath)
            .putString(KEY_ALLOWED_IP, settings.allowedRaspberryPiIp)
            .putInt(KEY_N_CTX, settings.nCtx)
            .putInt(KEY_N_THREADS, settings.nThreads)
            .putInt(KEY_MAX_TOKENS, settings.maxTokens)
            .putFloat(KEY_TEMPERATURE, settings.temperature)
            .putBoolean(KEY_AUTO_START, settings.autoStartServer)
            .putBoolean(KEY_AUTO_LOAD, settings.autoLoadModel)
            .putBoolean(KEY_KEEP_ALIVE, settings.keepAliveInBackground)
            .putString(KEY_SYSTEM_PROMPT, settings.systemPrompt)
            .apply()
    }
    fun regenerateToken(): String = generateToken().also { prefs.edit().putString(KEY_TOKEN, it).apply() }
    private fun generateToken(): String {
        val bytes = ByteArray(24); SecureRandom().nextBytes(bytes)
        return bytes.joinToString("") { "%02x".format(it) }
    }
    private companion object {
        const val KEY_PORT = "port"
        const val KEY_TOKEN = "api_token"
        const val KEY_MODEL_PATH = "model_path"
        const val KEY_ALLOWED_IP = "allowed_ip"
        const val KEY_N_CTX = "n_ctx"
        const val KEY_N_THREADS = "n_threads"
        const val KEY_MAX_TOKENS = "max_tokens"
        const val KEY_TEMPERATURE = "temperature"
        const val KEY_AUTO_START = "auto_start"
        const val KEY_AUTO_LOAD = "auto_load"
        const val KEY_KEEP_ALIVE = "keep_alive"
        const val KEY_SYSTEM_PROMPT = "system_prompt"
    }
}
