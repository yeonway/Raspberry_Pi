package com.local.kiwoompocket.ui.stockdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.data.model.ChartPoint
import com.local.kiwoompocket.data.model.OrderBookResponse
import com.local.kiwoompocket.data.model.QuoteResponse
import com.local.kiwoompocket.data.repository.StockRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class StockDetailUiState(
    val code: String = "005930",
    val loading: Boolean = false,
    val quote: QuoteResponse? = null,
    val orderBook: OrderBookResponse? = null,
    val dayChart: List<ChartPoint> = emptyList(),
    val minuteChart: List<ChartPoint> = emptyList(),
    val error: String? = null,
)

class StockDetailViewModel(private val stockRepository: StockRepository) : ViewModel() {
    private val _state = MutableStateFlow(StockDetailUiState())
    val state: StateFlow<StockDetailUiState> = _state.asStateFlow()

    fun setCode(code: String) {
        if (_state.value.code == code && _state.value.quote != null) return
        _state.update { it.copy(code = code.ifBlank { "005930" }) }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            val code = _state.value.code
            _state.update { it.copy(loading = true, error = null) }
            val quote = stockRepository.quote(code)
            val book = stockRepository.orderBook(code)
            val day = stockRepository.dayChart(code)
            val minute = stockRepository.minuteChart(code)
            _state.update {
                it.copy(
                    loading = false,
                    quote = (quote as? NetworkResult.Success)?.data,
                    orderBook = (book as? NetworkResult.Success)?.data,
                    dayChart = (day as? NetworkResult.Success)?.data?.points.orEmpty(),
                    minuteChart = (minute as? NetworkResult.Success)?.data?.points.orEmpty(),
                    error = listOf(quote, book, day, minute).filterIsInstance<NetworkResult.Error>().firstOrNull()?.message,
                )
            }
        }
    }
}
