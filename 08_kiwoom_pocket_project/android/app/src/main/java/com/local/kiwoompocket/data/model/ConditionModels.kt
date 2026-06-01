package com.local.kiwoompocket.data.model

data class ConditionSummary(
    val seq: String = "",
    val name: String = "",
    val isFallback: Boolean = false,
)

data class ConditionRunRequest(
    val searchType: String = "0",
    val stexTp: String = "K",
    val contYn: String = "N",
    val nextKey: String = "",
)

data class ConditionRunResponse(
    val seq: String = "",
    val name: String = "",
    val results: List<QuoteResponse> = emptyList(),
    val isFallback: Boolean = false,
)
