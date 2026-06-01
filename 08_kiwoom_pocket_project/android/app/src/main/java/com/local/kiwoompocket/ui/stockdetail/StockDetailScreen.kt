package com.local.kiwoompocket.ui.stockdetail

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.local.kiwoompocket.core.util.DateTimeFormatters
import com.local.kiwoompocket.core.util.NumberFormatters
import com.local.kiwoompocket.ui.components.ErrorView
import com.local.kiwoompocket.ui.components.InfoCard
import com.local.kiwoompocket.ui.components.LoadingView
import com.local.kiwoompocket.ui.components.PriceText

@Composable
fun StockDetailScreen(state: StockDetailUiState, onRefresh: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoCard("현재가") {
            val quote = state.quote
            if (quote == null) {
                Text("${state.code} 데이터가 없습니다.")
            } else {
                Text("${quote.code} ${quote.name}", fontWeight = FontWeight.SemiBold)
                PriceText(value = quote.price, changeRate = quote.changeRate)
                Text("등락 ${NumberFormatters.won(quote.changePrice)} / 거래량 ${NumberFormatters.quantity(quote.volume)}")
            }
        }
        InfoCard("호가") {
            val book = state.orderBook
            if (book == null) {
                Text("호가 데이터가 없습니다.")
            } else {
                Text("매도")
                book.asks.take(5).forEach { level ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(NumberFormatters.won(level.price))
                        Text(NumberFormatters.quantity(level.qty))
                    }
                }
                Text("매수")
                book.bids.take(5).forEach { level ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(NumberFormatters.won(level.price))
                        Text(NumberFormatters.quantity(level.qty))
                    }
                }
            }
        }
        InfoCard("일봉") {
            if (state.dayChart.isEmpty()) Text("일봉 데이터가 없습니다.")
            state.dayChart.takeLast(8).forEach {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(DateTimeFormatters.compactDate(it.date))
                    Text(NumberFormatters.won(it.close))
                }
            }
        }
        InfoCard("분봉") {
            if (state.minuteChart.isEmpty()) Text("분봉 데이터가 없습니다.")
            state.minuteChart.takeLast(8).forEach {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(it.time ?: "-")
                    Text(NumberFormatters.won(it.close))
                }
            }
        }
        if (state.loading) LoadingView()
        state.error?.let { ErrorView(it, onRefresh) }
    }
}
