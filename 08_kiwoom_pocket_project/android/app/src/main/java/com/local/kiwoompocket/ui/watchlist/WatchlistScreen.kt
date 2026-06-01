package com.local.kiwoompocket.ui.watchlist

import androidx.compose.foundation.clickable
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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.local.kiwoompocket.core.util.NumberFormatters
import com.local.kiwoompocket.ui.components.ErrorView
import com.local.kiwoompocket.ui.components.InfoCard
import com.local.kiwoompocket.ui.components.LoadingView
import com.local.kiwoompocket.ui.components.PriceText

@Composable
fun WatchlistScreen(
    state: WatchlistUiState,
    onAdd: (String, String) -> Unit,
    onDelete: (String) -> Unit,
    onRefresh: () -> Unit,
    onRefreshQuote: (String) -> Unit,
    onOpenDetail: (String) -> Unit,
    onRealtimeConnect: () -> Unit,
    onRealtimeDisconnect: () -> Unit,
) {
    var code by remember { mutableStateOf("") }
    var memo by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoCard("관심종목 추가") {
            OutlinedTextField(
                value = code,
                onValueChange = { code = it },
                label = { Text("종목코드") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = memo,
                onValueChange = { memo = it },
                label = { Text("메모") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = { onAdd(code, memo) }) {
                Text("추가")
            }
        }
        InfoCard("실시간 연결") {
            Text(if (state.realtimeState.connected) "연결됨" else "연결 안 됨")
            Text(state.realtimeState.message)
            if (state.realtimeState.lastPayload.isNotBlank()) {
                Text(state.realtimeState.lastPayload.take(120))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onRealtimeConnect) { Text("연결") }
                OutlinedButton(onClick = onRealtimeDisconnect) { Text("해제") }
            }
        }
        InfoCard("관심종목") {
            if (state.items.isEmpty()) {
                Text("관심종목이 없습니다.")
            } else {
                state.items.forEach { item ->
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onOpenDetail(item.code) }
                            .padding(vertical = 6.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${item.code} ${item.name}", fontWeight = FontWeight.SemiBold)
                            OutlinedButton(onClick = { onDelete(item.code) }) { Text("삭제") }
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { onRefreshQuote(item.code) }) { Text("현재가") }
                            OutlinedButton(onClick = { onOpenDetail(item.code) }) { Text("상세") }
                        }
                    }
                }
            }
        }
        state.lastQuote?.let {
            InfoCard("최근 현재가") {
                Text("${it.code} ${it.name}")
                PriceText(value = it.price, changeRate = it.changeRate)
                Text("거래량 ${NumberFormatters.quantity(it.volume)}")
            }
        }
        if (state.loading) LoadingView()
        state.error?.let { ErrorView(it, onRefresh) }
    }
}
