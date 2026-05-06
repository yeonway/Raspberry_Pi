package com.example.phoneaibridge.ui

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.example.phoneaibridge.Graph
import com.example.phoneaibridge.network.NetworkInfo
import com.example.phoneaibridge.network.NetworkInfoProvider
import com.example.phoneaibridge.server.ServerState
import com.example.phoneaibridge.service.AiBridgeForegroundService
import kotlinx.coroutines.launch

@Composable
fun HomeScreen() {
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val state by ServerState.snapshot.collectAsState()
    val count by Graph.aiRequestLogRepository.observeCount().collectAsState(initial = 0)
    val error by Graph.aiRequestLogRepository.observeLatestError().collectAsState(initial = null)
    val scope = rememberCoroutineScope()
    var networkInfo by remember { mutableStateOf(currentNetworkInfo()) }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("Phone AI Bridge MVP")
        Text("Server running: ${state.running}")
        Text("AI engine: MockAiEngine")
        Text("Current Phone IP: ${networkInfo.primaryIp ?: "not found"}")
        Text("Current Port: ${Graph.settings.read().port}")
        Text("API Base URL: ${networkInfo.apiBaseUrl ?: "not available"}")
        Text("Health URL: ${networkInfo.healthUrl ?: "not available"}")
        Text("All local IPs: ${networkInfo.localIps.joinToString().ifBlank { "none" }}")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { networkInfo = currentNetworkInfo() }) { Text("Refresh IP") }
            Button(
                enabled = networkInfo.apiBaseUrl != null,
                onClick = { networkInfo.apiBaseUrl?.let { clipboard.setText(AnnotatedString(it)) } },
            ) { Text("Copy API URL") }
            Button(
                enabled = networkInfo.healthUrl != null,
                onClick = { networkInfo.healthUrl?.let { clipboard.setText(AnnotatedString(it)) } },
            ) { Text("Copy Health URL") }
        }
        Text("Recent request count: $count")
        Text("Latest error: ${error ?: "none"}")
        Text("/health test result: ${state.lastHealthResult}")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { ContextCompat.startForegroundService(context, Intent(context, AiBridgeForegroundService::class.java)) }) { Text("Start Service") }
            Button(onClick = { context.stopService(Intent(context, AiBridgeForegroundService::class.java)) }) { Text("Stop Service") }
        }
        Button(
            onClick = {
                scope.launch {
                    ServerState.setHealthResult(Graph.apiRoutes.handle("GET", "/health", emptyMap(), "", null).body)
                    networkInfo = currentNetworkInfo()
                }
            },
        ) { Text("Test /health") }
    }
}

private fun currentNetworkInfo(): NetworkInfo {
    return NetworkInfoProvider.getNetworkInfo(Graph.settings.read().port)
}
