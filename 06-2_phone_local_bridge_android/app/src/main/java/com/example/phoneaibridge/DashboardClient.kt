package com.example.phoneaibridge

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URL
import java.nio.charset.StandardCharsets

object DashboardClient {
    const val DASHBOARD_URL = "http://172.30.1.8:8013"
    const val MINECRAFT_ADDRESS = "172.30.1.8:25565"

    fun get(path: String): JSONObject {
        return request("GET", path, null)
    }

    fun post(path: String, payload: JSONObject = JSONObject()): JSONObject {
        return request("POST", path, payload)
    }

    private fun request(method: String, path: String, payload: JSONObject?): JSONObject {
        val eventToken = BuildConfig.DASHBOARD_EVENT_TOKEN.trim()
        require(eventToken.isNotBlank()) { "dashboardEventToken is not configured in local.properties" }
        val url = URL(DASHBOARD_URL.trimEnd('/') + path)
        val bodyBytes = payload?.toString()?.toByteArray(StandardCharsets.UTF_8) ?: ByteArray(0)
        val target = url.file.takeIf { it.isNotBlank() } ?: "/"
        val port = if (url.port > 0) url.port else 80

        Socket().use { socket ->
            socket.connect(InetSocketAddress(url.host, port), 5000)
            socket.soTimeout = 10000
            val request = buildString {
                append("$method $target HTTP/1.1\r\n")
                append("Host: ${url.host}:$port\r\n")
                append("Accept: application/json\r\n")
                append("Connection: close\r\n")
                append("X-Event-Token: $eventToken\r\n")
                if (payload != null) {
                    append("Content-Type: application/json; charset=utf-8\r\n")
                    append("Content-Length: ${bodyBytes.size}\r\n")
                }
                append("\r\n")
            }

            val output = socket.getOutputStream()
            output.write(request.toByteArray(StandardCharsets.US_ASCII))
            if (bodyBytes.isNotEmpty()) output.write(bodyBytes)
            output.flush()

            val responseBytes = ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            val input = socket.getInputStream()
            var headerEnd = -1
            var contentLength: Int? = null
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                responseBytes.write(buffer, 0, read)
                val current = responseBytes.toByteArray()
                if (headerEnd < 0) {
                    headerEnd = findHeaderEnd(current)
                    if (headerEnd >= 0) {
                        val headers = String(current, 0, headerEnd, StandardCharsets.UTF_8)
                        contentLength = parseContentLength(headers)
                    }
                }
                if (headerEnd >= 0 && contentLength != null && current.size >= headerEnd + 4 + contentLength) {
                    break
                }
            }

            val response = responseBytes.toByteArray()
            val finalHeaderEnd = findHeaderEnd(response)
            require(finalHeaderEnd >= 0) { "invalid HTTP response" }
            val headers = String(response, 0, finalHeaderEnd, StandardCharsets.UTF_8)
            val finalContentLength = parseContentLength(headers)
            val bodyStart = finalHeaderEnd + 4
            val bodyLength = finalContentLength ?: (response.size - bodyStart)
            val body = String(response, bodyStart, bodyLength.coerceAtMost(response.size - bodyStart), StandardCharsets.UTF_8)
            val status = headers.lineSequence()
                .firstOrNull()
                ?.split(" ")
                ?.getOrNull(1)
                ?.toIntOrNull()
                ?: 0
            if (status !in 200..299) {
                throw IllegalStateException("HTTP $status $body")
            }
            return if (body.isBlank()) JSONObject() else JSONObject(body)
        }
    }

    private fun findHeaderEnd(bytes: ByteArray): Int {
        if (bytes.size < 4) return -1
        for (index in 0..(bytes.size - 4)) {
            if (
                bytes[index] == '\r'.code.toByte() &&
                bytes[index + 1] == '\n'.code.toByte() &&
                bytes[index + 2] == '\r'.code.toByte() &&
                bytes[index + 3] == '\n'.code.toByte()
            ) {
                return index
            }
        }
        return -1
    }

    private fun parseContentLength(headers: String): Int? {
        return headers.lineSequence()
            .firstOrNull { it.startsWith("Content-Length:", ignoreCase = true) }
            ?.substringAfter(":")
            ?.trim()
            ?.toIntOrNull()
    }
}
