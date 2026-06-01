package com.local.kiwoompocket.data.model

data class QuoteResponse(
    val code: String = "",
    val name: String = "",
    val price: Long = 0,
    val changePrice: Long = 0,
    val changeRate: Double = 0.0,
    val volume: Long = 0,
    val updatedAt: String = "",
    val isFallback: Boolean = false,
)

data class OrderBookLevel(
    val price: Long = 0,
    val qty: Long = 0,
)

data class OrderBookResponse(
    val code: String = "",
    val asks: List<OrderBookLevel> = emptyList(),
    val bids: List<OrderBookLevel> = emptyList(),
    val updatedAt: String = "",
    val isFallback: Boolean = false,
)

data class ChartPoint(
    val date: String = "",
    val time: String? = null,
    val open: Long = 0,
    val high: Long = 0,
    val low: Long = 0,
    val close: Long = 0,
    val volume: Long = 0,
)

data class ChartResponse(
    val code: String = "",
    val points: List<ChartPoint> = emptyList(),
    val isFallback: Boolean = false,
)

data class WatchStockRequest(
    val code: String,
    val name: String = "",
    val market: String = "KRX",
    val memo: String = "",
)

data class WatchStockResponse(
    val id: Long = 0,
    val code: String = "",
    val name: String = "",
    val market: String = "KRX",
    val memo: String = "",
    val createdAt: String = "",
)
