package com.local.kiwoompocket.data.repository

import com.local.kiwoompocket.core.database.RecentStockEntity
import com.local.kiwoompocket.core.database.StockDao
import com.local.kiwoompocket.core.datastore.SettingsDataStore
import com.local.kiwoompocket.core.network.ApiClient
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.core.network.safeApiCall
import com.local.kiwoompocket.data.model.ChartResponse
import com.local.kiwoompocket.data.model.OrderBookResponse
import com.local.kiwoompocket.data.model.QuoteResponse
import kotlinx.coroutines.flow.first

class StockRepository(
    private val settingsDataStore: SettingsDataStore,
    private val apiClient: ApiClient,
    private val stockDao: StockDao,
) {
    suspend fun quote(code: String): NetworkResult<QuoteResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        val result = when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.quote(code) }
        }
        if (result is NetworkResult.Success) {
            val q = result.data
            stockDao.upsertRecentStock(
                RecentStockEntity(
                    code = q.code,
                    name = q.name,
                    price = q.price,
                    changePrice = q.changePrice,
                    changeRate = q.changeRate,
                    volume = q.volume,
                )
            )
        }
        return result
    }

    suspend fun orderBook(code: String): NetworkResult<OrderBookResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.orderBook(code) }
        }
    }

    suspend fun dayChart(code: String): NetworkResult<ChartResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.dayChart(code) }
        }
    }

    suspend fun minuteChart(code: String): NetworkResult<ChartResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        return when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.minuteChart(code) }
        }
    }
}
