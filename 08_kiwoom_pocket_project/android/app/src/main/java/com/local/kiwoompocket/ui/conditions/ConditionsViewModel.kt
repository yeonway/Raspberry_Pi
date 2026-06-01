package com.local.kiwoompocket.ui.conditions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.data.model.ConditionSummary
import com.local.kiwoompocket.data.model.QuoteResponse
import com.local.kiwoompocket.data.repository.ConditionRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ConditionsUiState(
    val loading: Boolean = false,
    val conditions: List<ConditionSummary> = emptyList(),
    val selectedName: String = "",
    val results: List<QuoteResponse> = emptyList(),
    val error: String? = null,
)

class ConditionsViewModel(private val conditionRepository: ConditionRepository) : ViewModel() {
    private val _state = MutableStateFlow(ConditionsUiState())
    val state: StateFlow<ConditionsUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val result = conditionRepository.conditions()
            _state.update {
                it.copy(
                    loading = false,
                    conditions = (result as? NetworkResult.Success)?.data.orEmpty(),
                    error = (result as? NetworkResult.Error)?.message,
                )
            }
        }
    }

    fun run(seq: String, name: String) {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, selectedName = name, error = null) }
            val result = conditionRepository.run(seq)
            _state.update {
                it.copy(
                    loading = false,
                    results = (result as? NetworkResult.Success)?.data?.results.orEmpty(),
                    error = (result as? NetworkResult.Error)?.message,
                )
            }
        }
    }
}
