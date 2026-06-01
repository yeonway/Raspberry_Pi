package com.example.phoneaibridge

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.atomic.AtomicLong

object BridgeRuntime {
    const val PORT = 8765

    @Volatile var running: Boolean = false
        private set
    @Volatile var startedAtMillis: Long = 0
        private set
    @Volatile var lastPath: String = ""
        private set
    @Volatile var lastQuestion: String = ""
        private set
    @Volatile var lastAnswer: String = ""
        private set
    @Volatile var lastError: String = ""
        private set

    private val requestCounter = AtomicLong(0)

    fun markStarted() {
        running = true
        startedAtMillis = System.currentTimeMillis()
        lastError = ""
    }

    fun markStopped(error: String = "") {
        running = false
        if (error.isNotBlank()) lastError = error
    }

    fun recordRequest(path: String) {
        requestCounter.incrementAndGet()
        lastPath = path
    }

    fun recordAsk(question: String, answer: String) {
        lastQuestion = question
        lastAnswer = answer
    }

    fun recordError(error: String) {
        lastError = error
    }

    fun snapshot(context: Context): JSONObject {
        val addresses = NetworkInfo.localIpv4Addresses()
        val address = addresses.firstOrNull() ?: "0.0.0.0"
        return JSONObject()
            .put("ok", true)
            .put("running", running)
            .put("port", PORT)
            .put("url", "http://$address:$PORT")
            .put("addresses", JSONArray(addresses))
            .put("requestCount", requestCounter.get())
            .put("coordinateCount", CoordinateStore.count(context))
            .put("ai", PhoneLlamaEngine.snapshot(context))
            .put("startedAt", formatTime(startedAtMillis))
            .put("lastPath", lastPath)
            .put("lastQuestion", lastQuestion)
            .put("lastAnswer", lastAnswer)
            .put("lastError", lastError)
    }

    private fun formatTime(timeMillis: Long): String {
        if (timeMillis <= 0) return ""
        return SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.KOREA).format(Date(timeMillis))
    }
}
