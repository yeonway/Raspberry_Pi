package com.local.kiwoompocket.ui.orders

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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.local.kiwoompocket.ui.components.InfoCard
import com.local.kiwoompocket.ui.components.LoadingView

@Composable
fun MockOrderScreen(
    state: MockOrderUiState,
    onCodeChange: (String) -> Unit,
    onQtyChange: (String) -> Unit,
    onPriceChange: (String) -> Unit,
    onBuy: () -> Unit,
    onSell: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoCard("모의투자 주문") {
            Text("실전 주문은 기본 비활성화되어 있습니다.")
            Text(if (state.settings.isMockMode) "모의 모드에서만 서버 검증 요청이 가능합니다." else "실전모드에서는 사용 불가")
        }
        InfoCard("주문 입력") {
            OutlinedTextField(
                value = state.code,
                onValueChange = onCodeChange,
                label = { Text("종목코드") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = state.qty,
                onValueChange = onQtyChange,
                label = { Text("수량") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = state.price,
                onValueChange = onPriceChange,
                label = { Text("지정가") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(enabled = state.settings.isMockMode, onClick = onBuy) { Text("모의 매수") }
                Button(enabled = state.settings.isMockMode, onClick = onSell) { Text("모의 매도") }
            }
        }
        InfoCard("결과") {
            Text(state.message)
        }
        if (state.loading) LoadingView()
    }
}
