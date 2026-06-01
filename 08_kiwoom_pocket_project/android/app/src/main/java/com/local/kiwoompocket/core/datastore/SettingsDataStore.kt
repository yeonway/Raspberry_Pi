package com.local.kiwoompocket.core.datastore

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.settingsStore by preferencesDataStore(name = "kiwoom_pocket_settings")

class SettingsDataStore(private val context: Context) {
    private object Keys {
        val serverBaseUrl = stringPreferencesKey("server_base_url")
        val bridgeApiToken = stringPreferencesKey("bridge_api_token")
        val isMockMode = booleanPreferencesKey("is_mock_mode")
        val refreshIntervalSec = intPreferencesKey("refresh_interval_sec")
    }

    val settings: Flow<AppSettings> = context.settingsStore.data.map { prefs ->
        AppSettings(
            serverBaseUrl = prefs[Keys.serverBaseUrl].orEmpty(),
            bridgeApiToken = prefs[Keys.bridgeApiToken].orEmpty(),
            isMockMode = prefs[Keys.isMockMode] ?: true,
            refreshIntervalSec = prefs[Keys.refreshIntervalSec] ?: 10,
        )
    }

    suspend fun save(settings: AppSettings) {
        context.settingsStore.edit { prefs ->
            prefs[Keys.serverBaseUrl] = settings.serverBaseUrl.trim()
            prefs[Keys.bridgeApiToken] = settings.bridgeApiToken.trim()
            prefs[Keys.isMockMode] = settings.isMockMode
            prefs[Keys.refreshIntervalSec] = settings.refreshIntervalSec.coerceIn(3, 3600)
        }
    }
}
