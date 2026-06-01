package com.local.kiwoompocket.core.network

sealed interface NetworkResult<out T> {
    data class Success<T>(val data: T) : NetworkResult<T>
    data class Error(val message: String, val statusCode: Int? = null) : NetworkResult<Nothing>
}
