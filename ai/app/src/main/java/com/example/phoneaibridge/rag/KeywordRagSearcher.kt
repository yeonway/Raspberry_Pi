package com.example.phoneaibridge.rag

import com.example.phoneaibridge.db.dao.RagChunkDao
import com.example.phoneaibridge.db.entity.RagChunkEntity

class KeywordRagSearcher(private val dao: RagChunkDao? = null, private val inMemoryChunks: suspend () -> List<RagChunkEntity> = { emptyList() }) : RagSearcher {
    override suspend fun search(query: String, limit: Int): List<RagResult> {
        val terms = query.lowercase().split(Regex("[\\s,/?]+")).map { it.trim() }.filter { it.length >= 2 }.distinct()
        if (terms.isEmpty()) return emptyList()
        val chunks = dao?.getAll() ?: inMemoryChunks()
        return chunks.mapNotNull { chunk ->
            val haystack = "${chunk.title} ${chunk.tags} ${chunk.chunkText}".lowercase()
            val score = terms.sumOf { term ->
                val titleBoost = if (chunk.title.lowercase().contains(term)) 2.0 else 0.0
                val tagBoost = if (chunk.tags.lowercase().contains(term)) 1.5 else 0.0
                val bodyHits = Regex.escape(term).toRegex().findAll(haystack).count() * 1.0
                titleBoost + tagBoost + bodyHits
            } / terms.size
            if (score > 0.0) RagResult(chunk.title, chunk.chunkText, score.coerceAtMost(1.0), chunk.tags) else null
        }.sortedByDescending { it.score }.take(limit.coerceAtLeast(1))
    }
}
