package com.example.phoneaibridge.ai

object LlamaNative {
    init {
        System.loadLibrary("phone_ai_llama")
    }

    external fun loadModel(modelPath: String, nCtx: Int, nThreads: Int): Long
    external fun freeModel(handle: Long)
    external fun isLoaded(handle: Long): Boolean
    external fun generate(handle: Long, prompt: String, maxTokens: Int, temperature: Float, topK: Int, topP: Float): String
}
