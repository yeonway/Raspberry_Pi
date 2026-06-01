package com.local.kiwoompocket.data.repository

import com.local.kiwoompocket.core.datastore.SettingsDataStore
import com.local.kiwoompocket.core.network.ApiClient
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.core.network.safeApiCall
import com.local.kiwoompocket.data.model.AccountNumbersResponse
import com.local.kiwoompocket.data.model.BalanceResponse
import com.local.kiwoompocket.data.model.HealthResponse
import com.local.kiwoompocket.data.model.PortfolioResponse
import com.local.kiwoompocket.data.model.TokenStatusResponse
import kotlinx.coroutines.flow.first

class AccountRepository(
    private val settingsDataStore: SettingsDataStore,
    private val apiClient: ApiClient,
) {
    suspend fun health(): NetworkResult<HealthResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.health() }
        }
    }

    suspend fun tokenStatus(): NetworkResult<TokenStatusResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.tokenStatus() }
        }
    }

    suspend fun refreshToken(): NetworkResult<TokenStatusResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.refreshToken() }
        }
    }

    suspend fun accountNumbers(): NetworkResult<AccountNumbersResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.accountNumbers() }
        }
    }

    suspend fun balance(): NetworkResult<BalanceResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.balance() }
        }
    }

    suspend fun portfolio(): NetworkResult<PortfolioResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.portfolio() }
        }
    }
}
