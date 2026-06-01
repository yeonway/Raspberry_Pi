package com.local.kiwoompocket.ui.conditions

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.local.kiwoompocket.core.util.NumberFormatters
import com.local.kiwoompocket.ui.components.ErrorView
import com.local.kiwoompocket.ui.components.InfoCard
import com.local.kiwoompocket.ui.components.LoadingView
import com.local.kiwoompocket.ui.components.PriceText

@Composable
fun ConditionsScreen(state: ConditionsUiState, onRefresh: () -> Unit, onRun: (String, String) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoCard("조건검색식") {
            if (state.conditions.isEmpty()) {
                Text("조건검색식이 없습니다.")
            } else {
                state.conditions.forEach { condition ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("${condition.seq} ${condition.name}", fontWeight = FontWeight.SemiBold)
                        OutlinedButton(onClick = { onRun(condition.seq, condition.name) }) {
                            Text("실행")
                        }
                    }
                }
            }
        }
        InfoCard("실행 결과") {
            if (state.selectedName.isNotBlank()) {
                Text(state.selectedName, fontWeight = FontWeight.SemiBold)
            }
            if (state.results.isEmpty()) {
                Text("결과가 없습니다.")
            } else {
                state.results.forEach { item ->
                    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text("${item.code} ${item.name}", fontWeight = FontWeight.SemiBold)
                        PriceText(value = item.price, changeRate = item.changeRate)
                        Text("거래량 ${NumberFormatters.quantity(item.volume)}")
                    }
                }
            }
        }
        if (state.loading) LoadingView()
        state.error?.let { ErrorView(it, onRefresh) }
    }
}
