package com.local.kiwoompocket.core.network

import com.local.kiwoompocket.core.datastore.SettingsDataStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

data class RealtimeState(
    val connected: Boolean = false,
    val message: String = "연결 안 됨",
    val lastPayload: String = "",
)

class WebSocketManager(private val settingsDataStore: SettingsDataStore) {
    private val client = OkHttpClient.Builder()
        .pingInterval(20, TimeUnit.SECONDS)
        .build()
    private var webSocket: WebSocket? = null
    private val _state = MutableStateFlow(RealtimeState())
    val state: StateFlow<RealtimeState> = _state

    suspend fun connect(codes: List<String>) {
        val settings = settingsDataStore.settings.first()
        if (settings.serverBaseUrl.isBlank()) {
            _state.value = RealtimeState(message = "서버 주소를 먼저 설정하세요.")
            return
        }
        disconnect()
        val url = wsUrl(settings.serverBaseUrl)
        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer ${settings.bridgeApiToken}")
            .build()
        webSocket = client.newWebSocket(
            request,
            object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    _state.value = RealtimeState(connected = true, message = "실시간 연결됨")
                    webSocket.send("""{"action":"subscribe","codes":${codes.joinToString(prefix = "[", postfix = "]") { "\"$it\"" }}}""")
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    _state.value = _state.value.copy(connected = true, message = "수신 중", lastPayload = text)
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    _state.value = RealtimeState(message = t.message ?: "실시간 연결 실패")
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    _state.value = RealtimeState(message = "연결 종료: $reason")
                }
            },
        )
    }

    fun disconnect() {
        webSocket?.close(1000, "client close")
        webSocket = null
        _state.value = RealtimeState(message = "연결 안 됨")
    }

    private fun wsUrl(baseUrl: String): String {
        val normalized = ApiClient().normalizeBaseUrl(baseUrl)
        val withoutSlash = normalized.removeSuffix("/")
        return when {
            withoutSlash.startsWith("https://") -> withoutSlash.replaceFirst("https://", "wss://") + "/ws/realtime"
            withoutSlash.startsWith("http://") -> withoutSlash.replaceFirst("http://", "ws://") + "/ws/realtime"
            else -> "ws://$withoutSlash/ws/realtime"
        }
    }
}
