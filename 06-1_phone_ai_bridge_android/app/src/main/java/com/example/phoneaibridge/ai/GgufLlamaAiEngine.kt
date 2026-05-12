package com.example.phoneaibridge.ai

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

class GgufLlamaAiEngine : AiEngine {
    private val lock = Any()
    private var handle: Long = 0L
    private var loadedPath: String = ""
    private var lastError: String? = null

    suspend fun loadModel(modelPath: String, nCtx: Int, nThreads: Int): Boolean {
        val path = modelPath.trim()
        if (path.isBlank()) {
            lastError = "model path is blank"
            return false
        }

        return withContext(Dispatchers.Default) {
            synchronized(lock) {
                runCatching {
                    if (handle != 0L && loadedPath == path) return@synchronized true
                    if (handle != 0L) {
                        LlamaNative.freeModel(handle)
                        handle = 0L
                        loadedPath = ""
                    }

                    val modelFile = File(path)
                    if (!modelFile.exists()) {
                        error("file does not exist: $path")
                    }
                    if (!modelFile.isFile) {
                        error("path is not a file: $path")
                    }
                    if (!modelFile.canRead()) {
                        error("file is not readable. Allow All files access for Phone AI Bridge: $path")
                    }
                    if (modelFile.length() < MIN_GGUF_BYTES) {
                        error("file is too small for a GGUF model (${modelFile.length()} bytes): $path")
                    }

                    handle = LlamaNative.loadModel(path, nCtx.coerceIn(512, 4096), nThreads.coerceIn(1, 8))
                    loadedPath = if (handle != 0L) path else ""
                    lastError = null
                    handle != 0L
                }.getOrElse {
                    handle = 0L
                    loadedPath = ""
                    lastError = it.message ?: "unknown load error"
                    false
                }
            }
        }
    }

    override suspend fun loadModel(modelPath: String): Boolean = loadModel(modelPath, DEFAULT_CONTEXT_TOKENS, DEFAULT_THREADS)

    override suspend fun isLoaded(): Boolean = synchronized(lock) {
        handle != 0L && LlamaNative.isLoaded(handle)
    }

    fun unload() = synchronized(lock) {
        if (handle != 0L) {
            LlamaNative.freeModel(handle)
            handle = 0L
        }
        loadedPath = ""
    }

    override suspend fun generate(prompt: String, maxTokens: Int): String = generate(prompt, maxTokens, 0.7f)

    suspend fun generate(prompt: String, maxTokens: Int, temperature: Float): String {
        return withContext(Dispatchers.Default) {
            synchronized(lock) {
                if (handle == 0L) error("GGUF model is not loaded")
                LlamaNative.generate(
                    handle = handle,
                    prompt = prompt,
                    maxTokens = maxTokens.coerceIn(1, 512),
                    temperature = temperature.coerceIn(0.0f, 2.0f),
                    topK = 40,
                    topP = 0.9f,
                ).trim()
            }
        }
    }

    fun lastLoadError(): String? = synchronized(lock) { lastError }

    private companion object {
        const val DEFAULT_CONTEXT_TOKENS = 2048
        const val DEFAULT_THREADS = 4
        const val MIN_GGUF_BYTES = 1024L * 1024L
    }
}
