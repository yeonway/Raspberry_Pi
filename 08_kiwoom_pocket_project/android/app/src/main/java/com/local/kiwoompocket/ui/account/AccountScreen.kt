package com.local.kiwoompocket.ui.account

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.local.kiwoompocket.core.util.NumberFormatters
import com.local.kiwoompocket.ui.components.ErrorView
import com.local.kiwoompocket.ui.components.InfoCard
import com.local.kiwoompocket.ui.components.LoadingView
import com.local.kiwoompocket.ui.components.rateColor

@Composable
fun AccountScreen(state: AccountUiState, onRefresh: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoCard("계좌번호") {
            if (state.accounts.isEmpty()) Text("계좌번호가 없습니다.") else state.accounts.forEach { Text(it) }
        }
        InfoCard("예수금") {
            val balance = state.balance
            if (balance == null) {
                Text("잔고 데이터 없음")
            } else {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("예수금")
                    Text(NumberFormatters.won(balance.deposit), fontWeight = FontWeight.SemiBold)
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("주문 가능")
                    Text(NumberFormatters.won(balance.availableCash), fontWeight = FontWeight.SemiBold)
                }
            }
        }
        InfoCard("보유종목") {
            if (state.holdings.isEmpty()) {
                Text("보유종목 데이터가 없습니다.")
            } else {
                state.holdings.forEach { item ->
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text("${item.code} ${item.name}", fontWeight = FontWeight.SemiBold)
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${item.qty}주 / 평균 ${NumberFormatters.won(item.avgPrice)}")
                            Text(
                                "${NumberFormatters.won(item.evalProfit)} ${NumberFormatters.percent(item.profitRate)}",
                                color = rateColor(item.profitRate),
                            )
                        }
                    }
                }
            }
        }
        Text(
            text = "평가손익: ${NumberFormatters.won(state.totalProfit)}",
            color = rateColor(state.totalProfit.toDouble()),
            style = MaterialTheme.typography.titleMedium,
        )
        if (state.loading) LoadingView()
        state.error?.let { ErrorView(it, onRefresh) }
    }
}
