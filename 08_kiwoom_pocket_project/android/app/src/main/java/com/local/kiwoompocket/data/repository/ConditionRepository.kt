package com.local.kiwoompocket.data.repository

import com.local.kiwoompocket.core.datastore.SettingsDataStore
import com.local.kiwoompocket.core.network.ApiClient
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.core.network.safeApiCall
import com.local.kiwoompocket.data.model.ConditionRunRequest
import com.local.kiwoompocket.data.model.ConditionRunResponse
import com.local.kiwoompocket.data.model.ConditionSummary
import kotlinx.coroutines.flow.first

class ConditionRepository(
    private val settingsDataStore: SettingsDataStore,
    private val apiClient: ApiClient,
) {
    suspend fun conditions(): NetworkResult<List<ConditionSummary>> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.conditions() }
        }
    }

    suspend fun run(seq: String): NetworkResult<ConditionRunResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.runCondition(seq, ConditionRunRequest()) }
        }
    }
}
