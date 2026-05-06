package com.example.phoneaibridge.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.phoneaibridge.Graph

@Composable
fun LogsScreen() {
    val logs by Graph.aiRequestLogRepository.observeRecent(50).collectAsState(initial = emptyList())
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Logs")
        LazyColumn { items(logs) { log -> Column(Modifier.padding(vertical = 6.dp)) { Text("${log.playerName ?: "-"}: ${log.message}"); Text("answer: ${log.answer}"); Text("latency_ms: ${log.latencyMs} / ok: ${log.ok}"); Text("created_at: ${log.createdAt}"); if (log.errorMessage != null) Text("error: ${log.errorMessage}"); HorizontalDivider() } } }
    }
}
