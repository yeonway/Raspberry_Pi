package com.local.kiwoompocket.data.repository

import com.local.kiwoompocket.core.database.StockDao
import com.local.kiwoompocket.core.database.WatchStockEntity
import com.local.kiwoompocket.core.datastore.SettingsDataStore
import com.local.kiwoompocket.core.network.ApiClient
import com.local.kiwoompocket.core.network.NetworkResult
import com.local.kiwoompocket.core.network.safeApiCall
import com.local.kiwoompocket.data.model.WatchStockRequest
import com.local.kiwoompocket.data.model.WatchStockResponse
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first

class WatchlistRepository(
    private val settingsDataStore: SettingsDataStore,
    private val apiClient: ApiClient,
    private val stockDao: StockDao,
) {
    val localWatchlist: Flow<List<WatchStockEntity>> = stockDao.observeWatchStocks()

    suspend fun remoteWatchlist(): NetworkResult<List<WatchStockResponse>> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        val result = when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.watchlist() }
        }
        if (result is NetworkResult.Success) {
            result.data.forEach {
                stockDao.upsertWatchStock(WatchStockEntity(code = it.code, name = it.name, market = it.market, memo = it.memo))
            }
        }
        return result
    }

    suspend fun add(code: String, memo: String): NetworkResult<WatchStockResponse> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        val result = when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.addWatchStock(WatchStockRequest(code = code, memo = memo)) }
        }
        if (result is NetworkResult.Success) {
            val item = result.data
            stockDao.upsertWatchStock(WatchStockEntity(code = item.code, name = item.name, market = item.market, memo = item.memo))
        }
        return result
    }

    suspend fun delete(code: String): NetworkResult<Unit> {
        val settings = settingsDataStore.settings.first()
        val api = bridgeApiOrError(settings, apiClient)
        val result = when (api) {
            is NetworkResult.Error -> api
            is NetworkResult.Success -> safeApiCall { api.data.deleteWatchStock(code) }
        }
        if (result is NetworkResult.Success) {
            stockDao.deleteWatchStock(code)
        }
        return result
    }
}
