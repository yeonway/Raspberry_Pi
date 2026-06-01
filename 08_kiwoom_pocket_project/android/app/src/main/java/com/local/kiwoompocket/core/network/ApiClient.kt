package com.local.kiwoompocket.core.network

import com.google.gson.FieldNamingPolicy
import com.google.gson.GsonBuilder
import okhttp3.OkHttpClient
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class ApiClient {
    fun create(baseUrl: String, token: String): BridgeApi {
        val normalizedUrl = normalizeBaseUrl(baseUrl)
        val gson = GsonBuilder()
            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
            .create()
        val okHttp = OkHttpClient.Builder()
            .connectTimeout(8, TimeUnit.SECONDS)
            .readTimeout(12, TimeUnit.SECONDS)
            .writeTimeout(12, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val builder = chain.request().newBuilder()
                if (token.isNotBlank()) {
                    builder.header("Authorization", "Bearer $token")
                }
                chain.proceed(builder.build())
            }
            .build()

        return Retrofit.Builder()
            .baseUrl(normalizedUrl)
            .client(okHttp)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
            .create(BridgeApi::class.java)
    }

    fun normalizeBaseUrl(baseUrl: String): String {
        val trimmed = baseUrl.trim()
        val withScheme = when {
            trimmed.isBlank() -> "http://127.0.0.1:8000"
            trimmed.startsWith("http://") || trimmed.startsWith("https://") -> trimmed
            else -> "http://$trimmed"
        }
        return if (withScheme.endsWith("/")) withScheme else "$withScheme/"
    }
}

suspend fun <T> safeApiCall(call: suspend () -> Response<T>): NetworkResult<T> {
    return try {
        val response = call()
        val body = response.body()
        if (response.isSuccessful && body != null) {
            NetworkResult.Success(body)
        } else if (response.isSuccessful && response.code() == 204) {
            @Suppress("UNCHECKED_CAST")
            NetworkResult.Success(Unit as T)
        } else {
            val errorText = response.errorBody()?.string()?.takeIf { it.isNotBlank() }
            NetworkResult.Error(
                message = errorText ?: "서버 요청이 실패했습니다. HTTP ${response.code()}",
                statusCode = response.code(),
            )
        }
    } catch (exception: java.net.SocketTimeoutException) {
        NetworkResult.Error("네트워크 요청 시간이 초과되었습니다.")
    } catch (exception: java.io.IOException) {
        NetworkResult.Error("서버에 연결할 수 없습니다. 서버 주소와 네트워크를 확인하세요.")
    } catch (exception: Exception) {
        NetworkResult.Error(exception.message ?: "알 수 없는 오류가 발생했습니다.")
    }
}
