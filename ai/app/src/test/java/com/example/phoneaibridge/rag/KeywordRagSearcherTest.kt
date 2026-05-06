package com.example.phoneaibridge.rag

import com.example.phoneaibridge.db.entity.RagChunkEntity
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class KeywordRagSearcherTest {
    @Test fun ranksMatchingChunksFirst() = runTest {
        val searcher = KeywordRagSearcher(inMemoryChunks = { listOf(
            RagChunkEntity(knowledgeId = 1, title = "철팜 기본 조건", chunkText = "주민 침대 골렘 스폰 공간", tags = "iron_farm,golem"),
            RagChunkEntity(knowledgeId = 2, title = "네더 포탈", chunkText = "옵시디언과 라이터", tags = "nether"),
        ) })
        val results = searcher.search("철팜 골렘", 5)
        assertEquals("철팜 기본 조건", results.first().title)
        assertTrue(results.first().score > 0.0)
    }
}
