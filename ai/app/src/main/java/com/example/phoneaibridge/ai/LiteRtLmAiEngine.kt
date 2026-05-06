package com.example.phoneaibridge.ai

class LiteRtLmAiEngine : AiEngine {
    override suspend fun loadModel(modelPath: String): Boolean = false // TODO: add LiteRT-LM dependency and Gemma 4 E2B 4bit loading in phase 2.
    override suspend fun isLoaded(): Boolean = false
    override suspend fun generate(prompt: String, maxTokens: Int): String = "LiteRT-LM 엔진은 2차 작업에서 실제 구현 예정입니다."
}
