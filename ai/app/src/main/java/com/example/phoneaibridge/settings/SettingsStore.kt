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
            modelPath = prefs.getString(KEY_MODEL_PATH, "").orEmpty(),
            allowedRaspberryPiIp = prefs.getString(KEY_ALLOWED_IP, "").orEmpty(),
        )
    }
    fun save(settings: AppSettings) { prefs.edit().putInt(KEY_PORT, settings.port).putString(KEY_TOKEN, settings.apiToken).putString(KEY_MODEL_PATH, settings.modelPath).putString(KEY_ALLOWED_IP, settings.allowedRaspberryPiIp).apply() }
    fun regenerateToken(): String = generateToken().also { prefs.edit().putString(KEY_TOKEN, it).apply() }
    private fun generateToken(): String {
        val bytes = ByteArray(24); SecureRandom().nextBytes(bytes)
        return bytes.joinToString("") { "%02x".format(it) }
    }
    private companion object { const val KEY_PORT = "port"; const val KEY_TOKEN = "api_token"; const val KEY_MODEL_PATH = "model_path"; const val KEY_ALLOWED_IP = "allowed_ip" }
}
