package com.example.phoneaibridge.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.phoneaibridge.Graph
import com.example.phoneaibridge.network.NetworkInfoProvider

@Composable
fun SettingsScreen() {
    val initial = remember { Graph.settings.read() }
    var port by remember { mutableStateOf(initial.port.toString()) }
    var token by remember { mutableStateOf(initial.apiToken) }
    var allowedIp by remember { mutableStateOf(initial.allowedRaspberryPiIp) }
    var saved by remember { mutableStateOf("") }
    val currentPort = port.toIntOrNull() ?: 8765
    val networkInfo = NetworkInfoProvider.getNetworkInfo(currentPort)

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Settings")
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Server")
                Text("Current Phone IP: ${networkInfo.primaryIp ?: "not found"}")
                Text("Current API URL: ${networkInfo.apiBaseUrl ?: "not available"}")
                OutlinedTextField(port, { port = it }, label = { Text("Server Port") })
                OutlinedTextField(token, { token = it }, label = { Text("API Token") })
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { token = Graph.settings.regenerateToken() }) { Text("Regenerate Token") }
                }
            }
        }
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Access")
                OutlinedTextField(allowedIp, { allowedIp = it }, label = { Text("Allowed Raspberry Pi IP (blank = token only)") })
                Text("Model selection is on the Home screen. Galaxy S20 12GB target uses 2048 context / 4 threads by default.")
            }
        }
        Button(
            onClick = {
                Graph.settings.save(Graph.settings.read().copy(port = currentPort, apiToken = token, allowedRaspberryPiIp = allowedIp))
                saved = "Saved"
            },
        ) { Text("Save Settings") }
        Text(saved)
    }
}
