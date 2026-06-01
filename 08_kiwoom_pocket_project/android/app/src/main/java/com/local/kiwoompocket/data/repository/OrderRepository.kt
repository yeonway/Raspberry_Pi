package com.local.kiwoompocket.data.repository

import com.local.kiwoompocket.core.datastore.SettingsDataStore
import com.local.kiwoompocket.core.network.ApiClient
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.core.network.safeApiCall
import com.local.kiwoompocket.data.model.MockOrderRequest
import com.local.kiwoompocket.data.model.MockOrderResponse
import kotlinx.coroutines.flow.first

class OrderRepository(
    private val settingsDataStore: SettingsDataStore,
    private val apiClient: ApiClient,
) {
    suspend fun buy(request: MockOrderRequest): NetworkResult<MockOrderResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.mockBuy(request) }
        }
    }

    suspend fun sell(request: MockOrderRequest): NetworkResult<MockOrderResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.mockSell(request) }
        }
    }
}
