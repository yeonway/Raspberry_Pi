package com.local.kiwoompocket.ui.watchlist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.local.kiwoompocket.core.database.WatchStockEntity
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.core.network.RealtimeState
import com.local.kiwoompocket.core.network.WebSocketManager
import com.local.kiwoompocket.data.model.QuoteResponse
import com.local.kiwoompocket.data.repository.StockRepository
import com.local.kiwoompocket.data.repository.WatchlistRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class WatchlistUiState(
    val loading: Boolean = false,
    val items: List<WatchStockEntity> = emptyList(),
    val lastQuote: QuoteResponse? = null,
    val realtimeState: RealtimeState = RealtimeState(),
    val error: String? = null,
)

class WatchlistViewModel(
    private val watchlistRepository: WatchlistRepository,
    private val stockRepository: StockRepository,
    private val webSocketManager: WebSocketManager,
) : ViewModel() {
    private val _state = MutableStateFlow(WatchlistUiState())
    val state: StateFlow<WatchlistUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            watchlistRepository.localWatchlist.collect { items ->
                _state.update { it.copy(items = items) }
            }
        }
        viewModelScope.launch {
            webSocketManager.state.collect { realtime ->
                _state.update { it.copy(realtimeState = realtime) }
            }
        }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val result = watchlistRepository.remoteWatchlist()
            _state.update {
                it.copy(
                    loading = false,
                    error = (result as? NetworkResult.Error)?.message,
                )
            }
        }
    }

    fun add(code: String, memo: String) {
        viewModelScope.launch {
            val trimmed = code.trim()
            if (trimmed.isBlank()) {
                _state.update { it.copy(error = "종목코드를 입력하세요.") }
                return@launch
            }
            _state.update { it.copy(loading = true, error = null) }
            val result = watchlistRepository.add(trimmed, memo)
            _state.update { it.copy(loading = false, error = (result as? NetworkResult.Error)?.message) }
        }
    }

    fun delete(code: String) {
        viewModelScope.launch {
            val result = watchlistRepository.delete(code)
            _state.update { it.copy(error = (result as? NetworkResult.Error)?.message) }
        }
    }

    fun refreshQuote(code: String) {
        viewModelScope.launch {
            val result = stockRepository.quote(code)
            _state.update {
                it.copy(
                    lastQuote = (result as? NetworkResult.Success)?.data ?: it.lastQuote,
                    error = (result as? NetworkResult.Error)?.message,
                )
            }
        }
    }

    fun connectRealtime() {
        viewModelScope.launch {
            webSocketManager.connect(_state.value.items.map { it.code }.ifEmpty { listOf("005930") })
        }
    }

    fun disconnectRealtime() {
        webSocketManager.disconnect()
    }
}
