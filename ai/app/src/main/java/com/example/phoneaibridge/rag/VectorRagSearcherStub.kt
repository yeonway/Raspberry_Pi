package com.example.phoneaibridge.rag

class VectorRagSearcherStub : RagSearcher {
    override suspend fun search(query: String, limit: Int): List<RagResult> = emptyList() // TODO: replace with embedding/vector search in phase 2.
}
