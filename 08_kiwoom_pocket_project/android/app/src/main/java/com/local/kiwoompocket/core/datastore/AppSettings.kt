package com.local.kiwoompocket.core.datastore

data class AppSettings(
    val serverBaseUrl: String = "",
    val bridgeApiToken: String = "",
    val isMockMode: Boolean = true,
    val refreshIntervalSec: Int = 10,
)
