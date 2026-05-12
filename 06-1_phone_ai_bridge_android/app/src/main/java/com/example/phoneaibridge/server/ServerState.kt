package com.example.phoneaibridge.server

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class ServerSnapshot(
    val running: Boolean = false,
    val port: Int = 8765,
    val lastHealthResult: String = "Not tested yet",
)

object ServerState {
    private val _snapshot = MutableStateFlow(ServerSnapshot())
    val snapshot: StateFlow<ServerSnapshot> = _snapshot

    fun markRunning(port: Int) {
        _snapshot.value = _snapshot.value.copy(running = true, port = port)
    }

    fun markStopped() {
        _snapshot.value = _snapshot.value.copy(running = false)
    }

    fun setHealthResult(result: String) {
        _snapshot.value = _snapshot.value.copy(lastHealthResult = result)
    }
}
