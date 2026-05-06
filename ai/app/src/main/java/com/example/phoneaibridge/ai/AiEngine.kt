package com.example.phoneaibridge.ai

interface AiEngine {
    suspend fun loadModel(modelPath: String): Boolean
    suspend fun isLoaded(): Boolean
    suspend fun generate(prompt: String, maxTokens: Int = 160): String
}
