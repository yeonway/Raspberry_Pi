package com.local.kiwoompocket.data.repository

import com.local.kiwoompocket.core.datastore.AppSettings
import com.local.kiwoompocket.core.network.ApiClient
import com.local.kiwoompocket.core.network.BridgeApi
import com.local.kiwoompocket.core.network.NetworkResult

internal fun bridgeApiOrError(settings: AppSettings, apiClient: ApiClient): NetworkResult<BridgeApi> {
    if (settings.serverBaseUrl.isBlank()) {
        return NetworkResult.Error("서버 주소가 비어 있습니다. 설정 화면에서 FastAPI 서버 주소를 입력하세요.")
    }
    return NetworkResult.Success(apiClient.create(settings.serverBaseUrl, settings.bridgeApiToken))
}
