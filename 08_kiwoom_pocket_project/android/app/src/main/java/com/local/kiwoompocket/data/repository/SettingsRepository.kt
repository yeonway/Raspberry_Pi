package com.local.kiwoompocket.data.repository

import com.local.kiwoompocket.core.datastore.AppSettings
import com.local.kiwoompocket.core.datastore.SettingsDataStore
import kotlinx.coroutines.flow.Flow

class SettingsRepository(private val settingsDataStore: SettingsDataStore) {
    val settings: Flow<AppSettings> = settingsDataStore.settings

    suspend fun save(settings: AppSettings) {
        settingsDataStore.save(settings)
    }
}
