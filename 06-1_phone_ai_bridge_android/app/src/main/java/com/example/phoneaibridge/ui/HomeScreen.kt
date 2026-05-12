package com.example.phoneaibridge.ui

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.phoneaibridge.Graph
import com.example.phoneaibridge.db.entity.AiRequestLogEntity
import com.example.phoneaibridge.model.ModelSnapshot
import com.example.phoneaibridge.network.NetworkInfo
import com.example.phoneaibridge.network.NetworkInfoProvider
import com.example.phoneaibridge.server.ServerSnapshot
import com.example.phoneaibridge.server.ServerState
import com.example.phoneaibridge.service.AiBridgeForegroundService
import com.example.phoneaibridge.settings.AppSettings
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HomeScreen(viewModel: HomeViewModel = viewModel()) {
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val server by ServerState.snapshot.collectAsState()
    val model by Graph.modelStore.snapshot.collectAsState()
    val uiState by viewModel.uiState.collectAsState()
    val logs by Graph.aiRequestLogRepository.observeRecent(5).collectAsState(initial = emptyList())
    var networkRefresh by remember { mutableStateOf(0) }
    val networkInfo = remember(uiState.settings.port, server.port, networkRefresh) {
        NetworkInfoProvider.getNetworkInfo(uiState.settings.port)
    }
    val modelPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) viewModel.selectModel(uri)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Text("Phone AI Bridge", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)

        StatusSection(
            server = server,
            model = model,
            networkInfo = networkInfo,
            onCopyUrl = { networkInfo.apiBaseUrl?.let { clipboard.setText(AnnotatedString(it)) } },
            onRefreshIp = { networkRefresh++ },
        )

        ServerControls(
            onStart = { ContextCompat.startForegroundService(context, Intent(context, AiBridgeForegroundService::class.java)) },
            onStop = { context.stopService(Intent(context, AiBridgeForegroundService::class.java)) },
            onPickModel = { modelPicker.launch(arrayOf("*/*")) },
            busy = model.copying || model.loading || model.busy,
        )

        ModelSection(
            model = model,
            uiState = uiState,
            onLoad = viewModel::loadModel,
            onUnload = viewModel::unloadModel,
            onClear = viewModel::clearModel,
        )

        ChatTestSection(
            uiState = uiState,
            model = model,
            onSend = viewModel::generateGguf,
            onClear = viewModel::clearChat,
        )

        MinimalSettingsSection(
            settings = uiState.settings,
            onSave = viewModel::updateSettings,
            onRegenerateToken = viewModel::regenerateToken,
            onCopyToken = { token -> clipboard.setText(AnnotatedString(token)) },
        )

        SmallLogSection(logs = logs, lastHealth = uiState.healthResult.ifBlank { server.lastHealthResult })
    }
}

@Composable
private fun StatusSection(
    server: ServerSnapshot,
    model: ModelSnapshot,
    networkInfo: NetworkInfo,
    onCopyUrl: () -> Unit,
    onRefreshIp: () -> Unit,
) {
    PlainSection("Status") {
        StatusLine("Server", if (server.running) "ON" else "OFF")
        StatusLine("Phone IP", networkInfo.primaryIp ?: "Not available")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                StatusLabel("API URL")
                Text(
                    text = networkInfo.apiBaseUrl ?: "http://phone-ip:${server.port}",
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            OutlinedButton(onClick = onCopyUrl, enabled = networkInfo.apiBaseUrl != null) {
                Text("Copy")
            }
        }
        StatusLine("Model", if (model.selected) "Selected" else "No model selected")
        OutlinedButton(onClick = onRefreshIp, modifier = Modifier.fillMaxWidth()) {
            Text("Refresh IP")
        }
    }
}

@Composable
private fun ServerControls(
    onStart: () -> Unit,
    onStop: () -> Unit,
    onPickModel: () -> Unit,
    busy: Boolean,
) {
    PlainSection("Controls") {
        BigButton("Start Server", onClick = onStart)
        BigButton("Stop Server", onClick = onStop, secondary = true)
        BigButton("Pick GGUF Model", onClick = onPickModel, enabled = !busy)
    }
}

@Composable
private fun ModelSection(
    model: ModelSnapshot,
    uiState: HomeUiState,
    onLoad: () -> Unit,
    onUnload: () -> Unit,
    onClear: () -> Unit,
) {
    val busy = uiState.isCopying || uiState.isLoading || model.busy
    PlainSection("Model") {
        StatusLine("File", model.name.ifBlank { "No model selected" })
        StatusLine("Size", formatBytes(model.sizeBytes))
        StatusLine("Loaded", if (model.loaded) "YES" else "NO")
        if (model.lastMessage.isNotBlank()) ShortNote(model.lastMessage)
        model.lastError?.let { ErrorText(readableError(it)) }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(
                onClick = onLoad,
                enabled = model.selected && !model.loaded && !busy,
                modifier = Modifier.weight(1f),
            ) {
                Text("Load Model")
            }
            OutlinedButton(
                onClick = onUnload,
                enabled = model.loaded && !busy,
                modifier = Modifier.weight(1f),
            ) {
                Text("Unload")
            }
        }
        OutlinedButton(onClick = onClear, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
            Text("Clear Model")
        }
    }
}

@Composable
private fun ChatTestSection(
    uiState: HomeUiState,
    model: ModelSnapshot,
    onSend: (String) -> Unit,
    onClear: () -> Unit,
) {
    var input by remember { mutableStateOf("") }
    val lastAnswer = uiState.chatMessages.lastOrNull { it.role == "AI" }?.text
    val canSend = input.isNotBlank() && !uiState.isGenerating && !model.busy

    PlainSection("Chat Test") {
        OutlinedTextField(
            value = input,
            onValueChange = { input = it },
            label = { Text("Message") },
            enabled = !uiState.isGenerating,
            minLines = 2,
            maxLines = 4,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(
                onClick = {
                    val message = input.trim()
                    input = ""
                    onSend(message)
                },
                enabled = canSend,
                modifier = Modifier.weight(1f),
            ) {
                Text(if (uiState.isGenerating) "Sending..." else "Send")
            }
            OutlinedButton(onClick = onClear, modifier = Modifier.weight(1f)) {
                Text("Clear")
            }
        }

        if (uiState.isGenerating) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(modifier = Modifier.height(20.dp), strokeWidth = 2.dp)
                Text("Generating...", style = MaterialTheme.typography.bodySmall)
            }
        }
        if (!uiState.modelSelected) ShortNote("Pick a GGUF model before sending.")
        if (uiState.modelSelected && !uiState.modelLoaded) ShortNote("The selected model will load when needed.")
        uiState.errorMessage?.let { ErrorText(readableError(it)) }

        Text("Recent response", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
            shape = MaterialTheme.shapes.small,
        ) {
            Text(
                text = lastAnswer?.let(::readableError) ?: "No response yet.",
                modifier = Modifier.padding(12.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun MinimalSettingsSection(
    settings: AppSettings,
    onSave: (AppSettings) -> Unit,
    onRegenerateToken: () -> Unit,
    onCopyToken: (String) -> Unit,
) {
    var tokenText by remember(settings.apiToken) { mutableStateOf(settings.apiToken) }
    var allowedIpText by remember(settings.allowedRaspberryPiIp) { mutableStateOf(settings.allowedRaspberryPiIp) }
    var advanced by remember { mutableStateOf(false) }
    var portText by remember(settings.port) { mutableStateOf(settings.port.toString()) }
    var nCtxText by remember(settings.nCtx) { mutableStateOf(settings.nCtx.toString()) }
    var nThreadsText by remember(settings.nThreads) { mutableStateOf(settings.nThreads.toString()) }
    var maxTokensText by remember(settings.maxTokens) { mutableStateOf(settings.maxTokens.toString()) }
    var temperature by remember(settings.temperature) { mutableStateOf(settings.temperature) }
    var autoStart by remember(settings.autoStartServer) { mutableStateOf(settings.autoStartServer) }
    var autoLoad by remember(settings.autoLoadModel) { mutableStateOf(settings.autoLoadModel) }
    var keepAlive by remember(settings.keepAliveInBackground) { mutableStateOf(settings.keepAliveInBackground) }
    var systemPrompt by remember(settings.systemPrompt) {
        mutableStateOf(settings.systemPrompt.ifBlank { AppSettings.DEFAULT_SYSTEM_PROMPT })
    }

    fun currentSettings(): AppSettings {
        return settings.copy(
            port = portText.toIntOrNull()?.coerceIn(1024, 65535) ?: 8765,
            apiToken = tokenText.trim(),
            allowedRaspberryPiIp = allowedIpText.trim(),
            nCtx = nCtxText.toIntOrNull()?.coerceIn(512, 4096) ?: 2048,
            nThreads = nThreadsText.toIntOrNull()?.coerceIn(1, 8) ?: 4,
            maxTokens = maxTokensText.toIntOrNull()?.coerceIn(32, 512) ?: 256,
            temperature = temperature.coerceIn(0f, 2f),
            autoStartServer = autoStart,
            autoLoadModel = autoLoad,
            keepAliveInBackground = keepAlive,
            systemPrompt = systemPrompt.ifBlank { AppSettings.DEFAULT_SYSTEM_PROMPT },
        )
    }

    PlainSection("Settings") {
        OutlinedTextField(
            value = tokenText,
            onValueChange = { tokenText = it },
            label = { Text("API Token") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(onClick = { onCopyToken(tokenText) }, modifier = Modifier.weight(1f)) { Text("Copy Token") }
            OutlinedButton(onClick = onRegenerateToken, modifier = Modifier.weight(1f)) { Text("Regenerate") }
        }
        OutlinedTextField(
            value = allowedIpText,
            onValueChange = { allowedIpText = it },
            label = { Text("Allowed Raspberry Pi IP") },
            placeholder = { Text("Blank = token only") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = systemPrompt,
            onValueChange = { systemPrompt = it },
            label = { Text("System Prompt") },
            minLines = 3,
            maxLines = 6,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedButton(
            onClick = { systemPrompt = AppSettings.DEFAULT_SYSTEM_PROMPT },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Reset System Prompt")
        }
        Button(onClick = { onSave(currentSettings()) }, modifier = Modifier.fillMaxWidth()) {
            Text("Save Settings")
        }

        OutlinedButton(onClick = { advanced = !advanced }, modifier = Modifier.fillMaxWidth()) {
            Text(if (advanced) "Hide Advanced" else "Show Advanced")
        }
        if (advanced) {
            SmallTextField("Port", portText, { portText = it }, KeyboardType.Number)
            SmallTextField("n_ctx", nCtxText, { nCtxText = it }, KeyboardType.Number)
            SmallTextField("n_threads", nThreadsText, { nThreadsText = it }, KeyboardType.Number)
            SmallTextField("Max tokens", maxTokensText, { maxTokensText = it }, KeyboardType.Number)
            Text("Temperature %.2f".format(temperature), style = MaterialTheme.typography.labelMedium)
            Slider(value = temperature, onValueChange = { temperature = it }, valueRange = 0f..2f)
            SettingSwitch("Auto-start server", autoStart) { autoStart = it }
            SettingSwitch("Auto-load model", autoLoad) { autoLoad = it }
            SettingSwitch("Keep server in background", keepAlive) { keepAlive = it }
        }
    }
}

@Composable
private fun SmallLogSection(logs: List<AiRequestLogEntity>, lastHealth: String) {
    PlainSection("Recent") {
        if (lastHealth.isNotBlank() && lastHealth != "Not tested yet") {
            ShortNote("Health: ${readableError(lastHealth)}")
        }
        if (logs.isEmpty()) {
            Text("No request logs yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            logs.take(5).forEach { log ->
                val text = log.errorMessage ?: log.answer.ifBlank { log.message }
                Text(
                    text = "${formatTime(log.createdAt)} ${if (log.ok) "OK" else "ERR"} - ${readableError(text)}",
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun PlainSection(title: String, content: @Composable () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
            shape = MaterialTheme.shapes.small,
        ) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                content()
            }
        }
        HorizontalDivider()
    }
}

@Composable
private fun StatusLine(label: String, value: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        StatusLabel(label, Modifier.weight(0.42f))
        Text(
            text = value.ifBlank { "-" },
            modifier = Modifier.weight(0.58f),
            style = MaterialTheme.typography.bodyMedium,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun StatusLabel(label: String, modifier: Modifier = Modifier) {
    Text(
        text = label,
        modifier = modifier,
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun BigButton(label: String, onClick: () -> Unit, enabled: Boolean = true, secondary: Boolean = false) {
    val modifier = Modifier
        .fillMaxWidth()
        .height(52.dp)
    if (secondary) {
        OutlinedButton(onClick = onClick, enabled = enabled, modifier = modifier) { Text(label) }
    } else {
        Button(
            onClick = onClick,
            enabled = enabled,
            modifier = modifier,
            colors = ButtonDefaults.buttonColors(),
        ) {
            Text(label)
        }
    }
}

@Composable
private fun ShortNote(message: String) {
    Text(
        text = readableError(message),
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun ErrorText(message: String) {
    Text(
        text = message,
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.error,
    )
}

@Composable
private fun SmallTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    keyboardType: KeyboardType,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun SettingSwitch(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

private fun formatBytes(bytes: Long): String {
    if (bytes <= 0) return "-"
    val mib = bytes / 1024.0 / 1024.0
    return if (mib >= 1024) "%.2f GB".format(mib / 1024.0) else "%.1f MB".format(mib)
}

private fun formatTime(timestamp: Long): String {
    return SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(timestamp))
}

private fun readableError(message: String): String {
    val compact = message.lineSequence().firstOrNull().orEmpty().ifBlank { message }
    return compact.replace(Regex("\\s+"), " ").take(220)
}
