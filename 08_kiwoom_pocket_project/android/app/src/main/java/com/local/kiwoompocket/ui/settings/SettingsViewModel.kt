package com.local.kiwoompocket.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.local.kiwoompocket.core.datastore.AppSettings
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.data.repository.AccountRepository
import com.local.kiwoompocket.data.repository.SettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val settings: AppSettings = AppSettings(),
    val connectionMessage: String = "",
    val saving: Boolean = false,
)

class SettingsViewModel(
    private val settingsRepository: SettingsRepository,
    private val accountRepository: AccountRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            settingsRepository.settings.collect { settings ->
                _state.update { it.copy(settings = settings) }
            }
        }
    }

    fun updateServerBaseUrl(value: String) {
        _state.update { it.copy(settings = it.settings.copy(serverBaseUrl = value)) }
    }

    fun updateBridgeApiToken(value: String) {
        _state.update { it.copy(settings = it.settings.copy(bridgeApiToken = value)) }
    }

    fun updateMockMode(value: Boolean) {
        _state.update { it.copy(settings = it.settings.copy(isMockMode = value)) }
    }

    fun updateRefreshInterval(value: String) {
        val interval = value.toIntOrNull() ?: _state.value.settings.refreshIntervalSec
        _state.update { it.copy(settings = it.settings.copy(refreshIntervalSec = interval.coerceIn(3, 3600))) }
    }

    fun save() {
        viewModelScope.launch {
            saveCurrent("설정을 저장했습니다.")
        }
    }

    fun testConnection() {
        viewModelScope.launch {
            saveCurrent("설정을 저장했습니다.")
            val result = accountRepository.health()
            _state.update {
                it.copy(
                    connectionMessage = when (result) {
                        is NetworkResult.Success -> "연결 성공: ${result.data.service} / ${result.data.mode}"
                        is NetworkResult.Error -> result.message
                    }
                )
            }
        }
    }

    private suspend fun saveCurrent(message: String) {
        _state.update { it.copy(saving = true) }
        settingsRepository.save(_state.value.settings)
        _state.update { it.copy(saving = false, connectionMessage = message) }
    }
}
