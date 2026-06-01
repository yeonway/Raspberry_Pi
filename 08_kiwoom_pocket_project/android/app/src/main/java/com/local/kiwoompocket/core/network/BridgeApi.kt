package com.local.kiwoompocket.core.network

import com.local.kiwoompocket.data.model.AccountNumbersResponse
import com.local.kiwoompocket.data.model.BalanceResponse
import com.local.kiwoompocket.data.model.ChartResponse
import com.local.kiwoompocket.data.model.ConditionRunRequest
import com.local.kiwoompocket.data.model.ConditionRunResponse
import com.local.kiwoompocket.data.model.ConditionSummary
import com.local.kiwoompocket.data.model.HealthResponse
import com.local.kiwoompocket.data.model.MockOrderRequest
import com.local.kiwoompocket.data.model.MockOrderResponse
import com.local.kiwoompocket.data.model.OrderBookResponse
import com.local.kiwoompocket.data.model.PortfolioResponse
import com.local.kiwoompocket.data.model.QuoteResponse
import com.local.kiwoompocket.data.model.TokenStatusResponse
import com.local.kiwoompocket.data.model.WatchStockRequest
import com.local.kiwoompocket.data.model.WatchStockResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface BridgeApi {
    @GET("health")
    suspend fun health(): Response<HealthResponse>

    @GET("api/token/status")
    suspend fun tokenStatus(): Response<TokenStatusResponse>

    @POST("api/token/refresh")
    suspend fun refreshToken(): Response<TokenStatusResponse>

    @GET("api/account/numbers")
    suspend fun accountNumbers(): Response<AccountNumbersResponse>

    @GET("api/account/balance")
    suspend fun balance(): Response<BalanceResponse>

    @GET("api/account/portfolio")
    suspend fun portfolio(): Response<PortfolioResponse>

    @GET("api/stocks/{code}/quote")
    suspend fun quote(@Path("code") code: String): Response<QuoteResponse>

    @GET("api/stocks/{code}/orderbook")
    suspend fun orderBook(@Path("code") code: String): Response<OrderBookResponse>

    @GET("api/stocks/{code}/chart/day")
    suspend fun dayChart(@Path("code") code: String): Response<ChartResponse>

    @GET("api/stocks/{code}/chart/minute")
    suspend fun minuteChart(@Path("code") code: String): Response<ChartResponse>

    @GET("api/watchlist")
    suspend fun watchlist(): Response<List<WatchStockResponse>>

    @POST("api/watchlist")
    suspend fun addWatchStock(@Body request: WatchStockRequest): Response<WatchStockResponse>

    @DELETE("api/watchlist/{code}")
    suspend fun deleteWatchStock(@Path("code") code: String): Response<Unit>

    @GET("api/conditions")
    suspend fun conditions(): Response<List<ConditionSummary>>

    @POST("api/conditions/{seq}/run")
    suspend fun runCondition(@Path("seq") seq: String, @Body request: ConditionRunRequest): Response<ConditionRunResponse>

    @POST("api/orders/mock/buy")
    suspend fun mockBuy(@Body request: MockOrderRequest): Response<MockOrderResponse>

    @POST("api/orders/mock/sell")
    suspend fun mockSell(@Body request: MockOrderRequest): Response<MockOrderResponse>
}
