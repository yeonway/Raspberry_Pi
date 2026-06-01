package com.local.kiwoompocket.ui.orders

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.local.kiwoompocket.core.datastore.AppSettings
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.data.model.MockOrderRequest
import com.local.kiwoompocket.data.repository.OrderRepository
import com.local.kiwoompocket.data.repository.SettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MockOrderUiState(
    val settings: AppSettings = AppSettings(),
    val code: String = "",
    val qty: String = "1",
    val price: String = "",
    val message: String = "모의투자 주문 스켈레톤입니다. 기본 비활성 안내를 확인하세요.",
    val loading: Boolean = false,
)

class MockOrderViewModel(
    settingsRepository: SettingsRepository,
    private val orderRepository: OrderRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MockOrderUiState())
    val state: StateFlow<MockOrderUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            settingsRepository.settings.collect { settings ->
                _state.update { it.copy(settings = settings) }
            }
        }
    }

    fun updateCode(value: String) = _state.update { it.copy(code = value) }
    fun updateQty(value: String) = _state.update { it.copy(qty = value) }
    fun updatePrice(value: String) = _state.update { it.copy(price = value) }

    fun submit(side: String) {
        viewModelScope.launch {
            if (!_state.value.settings.isMockMode) {
                _state.update { it.copy(message = "실전모드에서는 사용할 수 없습니다.") }
                return@launch
            }
            val request = MockOrderRequest(
                code = _state.value.code.trim(),
                qty = _state.value.qty.toLongOrNull() ?: 0,
                price = _state.value.price.toLongOrNull() ?: 0,
            )
            _state.update { it.copy(loading = true) }
            val result = if (side == "buy") orderRepository.buy(request) else orderRepository.sell(request)
            _state.update {
                it.copy(
                    loading = false,
                    message = when (result) {
                        is NetworkResult.Success -> result.data.message
                        is NetworkResult.Error -> result.message
                    },
                )
            }
        }
    }
}
