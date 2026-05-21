package com.example.phoneaibridge.server

import com.example.phoneaibridge.settings.SettingsStore
import io.ktor.http.ContentType
import io.ktor.http.Headers
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.call
import io.ktor.server.cio.CIO
import io.ktor.server.cio.CIOApplicationEngine
import io.ktor.server.engine.EmbeddedServer
import io.ktor.server.engine.embeddedServer
import io.ktor.server.plugins.origin
import io.ktor.server.request.httpMethod
import io.ktor.server.request.receiveText
import io.ktor.server.request.uri
import io.ktor.server.response.respondText
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import java.util.Locale

class LocalHttpServer(private val settingsStore: SettingsStore, private val routes: ApiRoutes) {
    private var engine: EmbeddedServer<CIOApplicationEngine, CIOApplicationEngine.Configuration>? = null

    @Synchronized
    fun start(): Boolean {
        if (engine != null) return false
        val port = settingsStore.read().port
        return runCatching {
            engine = embeddedServer(CIO, host = "0.0.0.0", port = port) {
                routing {
                    get("/health") { call.forwardToRoutes() }
                    post("/api/ask") { call.forwardToRoutes() }
                    get("/api/player/{uuid}/memory") { call.forwardToRoutes() }
                    post("/api/player/{uuid}/memory") { call.forwardToRoutes() }
                    post("/api/rag/ingest") { call.forwardToRoutes() }
                    post("/api/rag/search") { call.forwardToRoutes() }
                    get("/api/coordinates") { call.forwardToRoutes() }
                    post("/api/coordinates") { call.forwardToRoutes() }
                    post("/api/coordinates/search") { call.forwardToRoutes() }
                    delete("/api/coordinates/{id}") { call.forwardToRoutes() }
                    get("/api/logs") { call.forwardToRoutes() }
                }
            }
            engine?.start(wait = false)
            ServerState.markRunning(port)
            true
        }.getOrElse {
            engine = null
            ServerState.markStopped()
            false
        }
    }

    @Synchronized
    fun stop() {
        engine?.stop(gracePeriodMillis = 500, timeoutMillis = 1_000)
        engine = null
        ServerState.markStopped()
    }

    fun isRunning(): Boolean = engine != null

    private suspend fun ApplicationCall.forwardToRoutes() {
        val response = routes.handle(
            method = request.httpMethod.value,
            rawPath = request.uri,
            headers = request.headers.lowercaseMap(),
            body = if (request.httpMethod.value == "POST") receiveText() else "",
            remoteIp = request.origin.remoteHost,
        )
        respondText(
            text = response.body,
            status = HttpStatusCode.fromValue(response.code),
            contentType = ContentType.parse(response.contentType),
        )
    }

    private fun Headers.lowercaseMap(): Map<String, String> {
        return names().associate { name ->
            name.lowercase(Locale.US) to (get(name) ?: "")
        }
    }
}
