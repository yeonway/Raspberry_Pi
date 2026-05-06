package com.example.phoneaibridge.rag

interface RagSearcher {
    suspend fun search(query: String, limit: Int = 5): List<RagResult>
}
