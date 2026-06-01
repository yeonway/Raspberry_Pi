package com.local.kiwoompocket.ui.account

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.data.model.BalanceResponse
import com.local.kiwoompocket.data.model.PortfolioItem
import com.local.kiwoompocket.data.repository.AccountRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AccountUiState(
    val loading: Boolean = false,
    val accounts: List<String> = emptyList(),
    val balance: BalanceResponse? = null,
    val holdings: List<PortfolioItem> = emptyList(),
    val totalProfit: Long = 0,
    val error: String? = null,
)

class AccountViewModel(private val accountRepository: AccountRepository) : ViewModel() {
    private val _state = MutableStateFlow(AccountUiState())
    val state: StateFlow<AccountUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val numbers = accountRepository.accountNumbers()
            val balance = accountRepository.balance()
            val portfolio = accountRepository.portfolio()
            _state.update {
                it.copy(
                    loading = false,
                    accounts = (numbers as? NetworkResult.Success)?.data?.accounts.orEmpty(),
                    balance = (balance as? NetworkResult.Success)?.data,
                    holdings = (portfolio as? NetworkResult.Success)?.data?.items.orEmpty(),
                    totalProfit = (portfolio as? NetworkResult.Success)?.data?.totalProfit ?: 0,
                    error = listOf(numbers, balance, portfolio).filterIsInstance<NetworkResult.Error>().firstOrNull()?.message,
                )
            }
        }
    }
}
