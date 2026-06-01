package com.local.kiwoompocket.data.model

data class HealthResponse(
    val status: String = "",
    val service: String = "",
    val mode: String = "",
    val mockFallback: Boolean = true,
)

data class TokenStatusResponse(
    val hasToken: Boolean = false,
    val expiresDt: String? = null,
    val expiresInSec: Int? = null,
    val maskedToken: String? = null,
    val mode: String = "",
    val hasCredentials: Boolean = false,
)

data class AccountNumbersResponse(
    val accounts: List<String> = emptyList(),
    val isFallback: Boolean = false,
)

data class BalanceResponse(
    val deposit: Long = 0,
    val availableCash: Long = 0,
    val totalAsset: Long = 0,
    val isFallback: Boolean = false,
)

data class PortfolioItem(
    val code: String = "",
    val name: String = "",
    val qty: Long = 0,
    val avgPrice: Long = 0,
    val currentPrice: Long = 0,
    val evalAmount: Long = 0,
    val evalProfit: Long = 0,
    val profitRate: Double = 0.0,
)

data class PortfolioResponse(
    val items: List<PortfolioItem> = emptyList(),
    val totalEvalAmount: Long = 0,
    val totalProfit: Long = 0,
    val isFallback: Boolean = false,
)
