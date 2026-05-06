package com.example.phoneaibridge.rag

data class RagResult(val title: String, val chunkText: String, val score: Double, val tags: String = "")
