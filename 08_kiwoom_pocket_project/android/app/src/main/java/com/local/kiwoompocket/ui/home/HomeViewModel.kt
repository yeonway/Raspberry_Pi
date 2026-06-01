package com.local.kiwoompocket.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.local.kiwoompocket.core.database.WatchStockEntity
import com.local.kiwoompocket.core.datastore.AppSettings
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.data.model.BalanceResponse
import com.local.kiwoompocket.data.model.TokenStatusResponse
import com.local.kiwoompocket.data.repository.AccountRepository
import com.local.kiwoompocket.data.repository.SettingsRepository
import com.local.kiwoompocket.data.repository.WatchlistRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val loading: Boolean = false,
    val serverMessage: String = "서버 주소 미설정",
    val tokenStatus: TokenStatusResponse? = null,
    val balance: BalanceResponse? = null,
    val watchlist: List<WatchStockEntity> = emptyList(),
    val settings: AppSettings = AppSettings(),
    val error: String? = null,
)

class HomeViewModel(
    private val accountRepository: AccountRepository,
    private val watchlistRepository: WatchlistRepository,
    settingsRepository: SettingsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(HomeUiState())
    val state: StateFlow<HomeUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            settingsRepository.settings.collect { settings ->
                _state.update { it.copy(settings = settings) }
            }
        }
        viewModelScope.launch {
            watchlistRepository.localWatchlist.collect { items ->
                _state.update { it.copy(watchlist = items) }
            }
        }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val health = accountRepository.health()
            val serverMessage = when (health) {
                is NetworkResult.Success -> "연결됨 (${health.data.mode}, fallback=${health.data.mockFallback})"
                is NetworkResult.Error -> health.message
            }
            val token = accountRepository.tokenStatus()
            val balance = accountRepository.balance()
            watchlistRepository.remoteWatchlist()
            _state.update {
                it.copy(
                    loading = false,
                    serverMessage = serverMessage,
                    tokenStatus = (token as? NetworkResult.Success)?.data,
                    balance = (balance as? NetworkResult.Success)?.data,
                    error = listOf(token, balance).filterIsInstance<NetworkResult.Error>().firstOrNull()?.message,
                )
            }
        }
    }
}
