package com.local.kiwoompocket.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.local.kiwoompocket.ui.components.InfoCard

@Composable
fun SettingsScreen(
    state: SettingsUiState,
    onServerChange: (String) -> Unit,
    onTokenChange: (String) -> Unit,
    onMockModeChange: (Boolean) -> Unit,
    onRefreshIntervalChange: (String) -> Unit,
    onSave: () -> Unit,
    onTest: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoCard("서버 설정") {
            OutlinedTextField(
                value = state.settings.serverBaseUrl,
                onValueChange = onServerChange,
                label = { Text("서버 주소") },
                placeholder = { Text("http://192.168.0.10:8000") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.settings.bridgeApiToken,
                onValueChange = onTokenChange,
                label = { Text("Bridge API 토큰") },
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.settings.refreshIntervalSec.toString(),
                onValueChange = onRefreshIntervalChange,
                label = { Text("새로고침 주기(초)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(if (state.settings.isMockMode) "모의 모드 표시" else "실전 모드 표시")
                Switch(checked = state.settings.isMockMode, onCheckedChange = onMockModeChange)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onSave) { Text("저장") }
                Button(onClick = onTest) { Text("연결 테스트") }
            }
        }
        InfoCard("보안") {
            Text("키움 API 키는 Android 앱에 저장하지 않습니다.")
            Text("Android 앱에는 FastAPI 서버 접속 토큰만 저장합니다.")
            Text("실전 주문은 기본 비활성화되어 있습니다.")
        }
        if (state.connectionMessage.isNotBlank()) {
            InfoCard("결과") {
                Text(state.connectionMessage)
            }
        }
    }
}
