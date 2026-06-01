package com.local.kiwoompocket.di

import android.content.Context
import androidx.room.Room
import com.local.kiwoompocket.core.database.AppDatabase
import com.local.kiwoompocket.core.datastore.SettingsDataStore
import com.local.kiwoompocket.core.network.ApiClient
import com.local.kiwoompocket.core.network.WebSocketManager
import com.local.kiwoompocket.data.repository.AccountRepository
import com.local.kiwoompocket.data.repository.ConditionRepository
import com.local.kiwoompocket.data.repository.OrderRepository
import com.local.kiwoompocket.data.repository.SettingsRepository
import com.local.kiwoompocket.data.repository.StockRepository
import com.local.kiwoompocket.data.repository.WatchlistRepository

class AppContainer(context: Context) {
    private val appContext = context.applicationContext
    val settingsDataStore = SettingsDataStore(appContext)
    private val apiClient = ApiClient()
    private val database = Room.databaseBuilder(
        appContext,
        AppDatabase::class.java,
        "kiwoom_pocket.db",
    ).build()

    val webSocketManager = WebSocketManager(settingsDataStore)
    val settingsRepository = SettingsRepository(settingsDataStore)
    val accountRepository = AccountRepository(settingsDataStore, apiClient)
    val stockRepository = StockRepository(settingsDataStore, apiClient, database.stockDao())
    val watchlistRepository = WatchlistRepository(settingsDataStore, apiClient, database.stockDao())
    val conditionRepository = ConditionRepository(settingsDataStore, apiClient)
    val orderRepository = OrderRepository(settingsDataStore, apiClient)
}
