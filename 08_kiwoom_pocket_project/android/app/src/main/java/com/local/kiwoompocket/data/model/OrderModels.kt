package com.local.kiwoompocket.data.model

data class MockOrderRequest(
    val code: String,
    val qty: Long,
    val price: Long,
    val orderType: String = "limit",
    val market: String = "KRX",
)

data class MockOrderResponse(
    val accepted: Boolean = false,
    val mode: String = "",
    val side: String = "",
    val code: String = "",
    val qty: Long = 0,
    val price: Long = 0,
    val orderType: String = "",
    val message: String = "",
)
