package com.example.phoneaibridge

import android.content.Context
import android.os.SystemClock
import android.util.Log
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketException
import java.nio.charset.StandardCharsets
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

class LocalHttpServer(
    private val context: Context,
    private val port: Int = BridgeRuntime.PORT,
) {
    private val running = AtomicBoolean(false)
    private val threadCounter = AtomicInteger(1)
    private var serverSocket: ServerSocket? = null
    private var acceptThread: Thread? = null
    private var executor: ExecutorService? = null

    @Synchronized
    fun start() {
        if (running.get()) return

        val socket = ServerSocket().apply {
            reuseAddress = true
            bind(InetSocketAddress("0.0.0.0", port))
        }
        val pool = Executors.newCachedThreadPool { runnable ->
            Thread(runnable, "phone-http-client-${threadCounter.getAndIncrement()}").apply {
                isDaemon = true
            }
        }

        serverSocket = socket
        executor = pool
        running.set(true)
        acceptThread = Thread({ acceptLoop(socket, pool) }, "phone-http-accept").apply {
            isDaemon = true
            start()
        }
        BridgeRuntime.markStarted()
    }

    @Synchronized
    fun stop() {
        running.set(false)
        runCatching { serverSocket?.close() }
        executor?.shutdownNow()
        acceptThread?.interrupt()
        serverSocket = null
        executor = null
        acceptThread = null
        BridgeRuntime.markStopped()
    }

    private fun acceptLoop(socket: ServerSocket, pool: ExecutorService) {
        while (running.get()) {
            try {
                val client = socket.accept()
                pool.execute { handleClient(client) }
            } catch (_: SocketException) {
                if (running.get()) BridgeRuntime.recordError("HTTP server socket closed")
                return
            } catch (error: Exception) {
                BridgeRuntime.recordError(error.message ?: error.javaClass.simpleName)
                Log.e(TAG, "accept failed", error)
            }
        }
    }

    private fun handleClient(socket: Socket) {
        socket.use { client ->
            client.soTimeout = 15_000
            try {
                val request = readRequest(client)
                val result = route(request)
                writeResponse(client, result)
            } catch (error: JSONException) {
                writeResponse(client, HttpResult(400, JSONObject().put("ok", false).put("error", "invalid json")))
            } catch (error: Exception) {
                BridgeRuntime.recordError(error.message ?: error.javaClass.simpleName)
                Log.e(TAG, "request failed", error)
                writeResponse(
                    client,
                    HttpResult(
                        500,
                        JSONObject()
                            .put("ok", false)
                            .put("error", error.message ?: error.javaClass.simpleName),
                    ),
                )
            }
        }
    }

    private fun route(request: HttpRequest): HttpResult {
        val path = request.path.substringBefore("?")
        if (request.method == "OPTIONS") return HttpResult(204, null)

        return when {
            request.method == "GET" && path == "/health" -> HttpResult(200, health())
            request.method == "POST" && path == "/api/ask" -> HttpResult(200, ask(request.body))
            request.method == "GET" && path == "/api/model/status" -> {
                HttpResult(200, PhoneLlamaEngine.snapshot(context).put("ok", true))
            }
            request.method == "POST" && path == "/api/model/load" -> {
                val ok = PhoneLlamaEngine.loadSelectedModel(context)
                val body = PhoneLlamaEngine.snapshot(context).put("ok", ok)
                if (!ok) body.put("error", body.optString("lastError"))
                HttpResult(if (ok) 200 else 500, body)
            }
            request.method == "POST" && path == "/api/model/unload" -> {
                PhoneLlamaEngine.unload()
                HttpResult(200, PhoneLlamaEngine.snapshot(context).put("ok", true))
            }
            request.method == "GET" && path == "/api/coordinates" -> HttpResult(200, listCoordinates())
            request.method == "POST" && path == "/api/coordinates" -> HttpResult(200, saveCoordinate(request.body))
            request.method == "GET" && path == "/api/knowledge" -> HttpResult(200, listKnowledge())
            request.method == "POST" && path == "/api/knowledge" -> HttpResult(200, saveKnowledge(request.body))
            else -> HttpResult(404, JSONObject().put("ok", false).put("error", "not found"))
        }
    }

    private fun health(): JSONObject {
        BridgeRuntime.recordRequest("/health")
        val snapshot = BridgeRuntime.snapshot(context)
        val ai = PhoneLlamaEngine.snapshot(context)
        return JSONObject()
            .put("ok", true)
            .put("status", "running")
            .put("modelLoaded", ai.optBoolean("loaded"))
            .put("modelName", ai.optString("modelName"))
            .put("mode", "phone-llama.cpp")
            .put("ai", ai)
            .put("port", port)
            .put("url", snapshot.optString("url"))
            .put("addresses", snapshot.optJSONArray("addresses") ?: JSONArray())
            .put("requestCount", snapshot.optLong("requestCount"))
            .put("coordinateCount", snapshot.optInt("coordinateCount"))
            .put("knowledgeCount", KnowledgeStore.count(context))
            .put("lastError", snapshot.optString("lastError"))
    }

    private fun ask(body: String): JSONObject {
        val started = SystemClock.elapsedRealtime()
        val payload = parseJson(body)
        BridgeRuntime.recordRequest("/api/ask")
        val generated = AnswerGenerator.generate(context, payload)
        val latency = SystemClock.elapsedRealtime() - started
        val question = payload.optString("message").ifBlank { payload.optString("question") }

        BridgeRuntime.recordAsk(question, generated.answer)

        return JSONObject()
            .put("answer", generated.answer)
            .put("usedMemory", false)
            .put("usedRag", generated.usedRag)
            .put("usedAi", generated.usedAi)
            .put("model", generated.model)
            .put("latencyMs", latency)
    }

    private fun saveCoordinate(body: String): JSONObject {
        BridgeRuntime.recordRequest("/api/coordinates")
        val coordinate = CoordinateStore.upsert(context, parseJson(body))
        return JSONObject()
            .put("ok", true)
            .put("saved", true)
            .put("id", coordinate.id)
            .put("count", CoordinateStore.count(context))
    }

    private fun listCoordinates(): JSONObject {
        BridgeRuntime.recordRequest("/api/coordinates")
        val items = JSONArray()
        CoordinateStore.list(context).forEach { items.put(it.toJson()) }
        return JSONObject()
            .put("ok", true)
            .put("count", items.length())
            .put("items", items)
    }

    private fun saveKnowledge(body: String): JSONObject {
        BridgeRuntime.recordRequest("/api/knowledge")
        val item = KnowledgeStore.upsert(context, parseJson(body))
        return JSONObject()
            .put("ok", true)
            .put("saved", true)
            .put("id", item.id)
            .put("count", KnowledgeStore.count(context))
    }

    private fun listKnowledge(): JSONObject {
        BridgeRuntime.recordRequest("/api/knowledge")
        val items = JSONArray()
        KnowledgeStore.list(context).forEach { items.put(it.toJson()) }
        return JSONObject()
            .put("ok", true)
            .put("count", items.length())
            .put("items", items)
    }

    private fun parseJson(body: String): JSONObject {
        if (body.isBlank()) return JSONObject()
        return JSONObject(body)
    }

    private fun readRequest(socket: Socket): HttpRequest {
        val input = BufferedInputStream(socket.getInputStream())
        val requestLine = readLine(input) ?: throw IllegalArgumentException("empty request")
        val parts = requestLine.split(" ")
        require(parts.size >= 2) { "invalid request line" }

        val headers = linkedMapOf<String, String>()
        while (true) {
            val line = readLine(input) ?: break
            if (line.isBlank()) break
            val separator = line.indexOf(':')
            if (separator > 0) {
                headers[line.substring(0, separator).trim().lowercase()] = line.substring(separator + 1).trim()
            }
        }

        val contentLength = headers["content-length"]?.toIntOrNull()?.coerceAtLeast(0) ?: 0
        val bodyBytes = ByteArray(contentLength)
        var offset = 0
        while (offset < contentLength) {
            val read = input.read(bodyBytes, offset, contentLength - offset)
            if (read < 0) break
            offset += read
        }

        return HttpRequest(
            method = parts[0].uppercase(),
            path = parts[1],
            body = String(bodyBytes, 0, offset, StandardCharsets.UTF_8),
        )
    }

    private fun readLine(input: BufferedInputStream): String? {
        val buffer = ByteArrayOutputStream()
        while (true) {
            val byte = input.read()
            if (byte < 0) {
                return if (buffer.size() == 0) null else buffer.toString(StandardCharsets.UTF_8.name())
            }
            if (byte == '\n'.code) break
            if (byte != '\r'.code) buffer.write(byte)
            require(buffer.size() <= 8192) { "HTTP line too long" }
        }
        return buffer.toString(StandardCharsets.UTF_8.name())
    }

    private fun writeResponse(socket: Socket, result: HttpResult) {
        val bodyBytes = result.body?.toString()?.toByteArray(StandardCharsets.UTF_8) ?: ByteArray(0)
        val headers = buildString {
            append("HTTP/1.1 ${result.status} ${reasonPhrase(result.status)}\r\n")
            append("Access-Control-Allow-Origin: *\r\n")
            append("Access-Control-Allow-Headers: Content-Type, X-API-Token\r\n")
            append("Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n")
            append("Connection: close\r\n")
            append("Content-Type: application/json; charset=utf-8\r\n")
            append("Content-Length: ${bodyBytes.size}\r\n")
            append("\r\n")
        }
        socket.getOutputStream().use { output ->
            output.write(headers.toByteArray(StandardCharsets.US_ASCII))
            output.write(bodyBytes)
            output.flush()
        }
    }

    private fun reasonPhrase(status: Int): String {
        return when (status) {
            200 -> "OK"
            204 -> "No Content"
            400 -> "Bad Request"
            404 -> "Not Found"
            else -> "Internal Server Error"
        }
    }

    private data class HttpRequest(
        val method: String,
        val path: String,
        val body: String,
    )

    private data class HttpResult(
        val status: Int,
        val body: JSONObject?,
    )

    private companion object {
        const val TAG = "PhoneLocalHttpServer"
    }
}
