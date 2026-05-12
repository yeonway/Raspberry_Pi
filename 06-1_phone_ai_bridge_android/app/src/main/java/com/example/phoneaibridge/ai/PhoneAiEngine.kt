package com.example.phoneaibridge.ai

import com.example.phoneaibridge.model.ModelStore
import com.example.phoneaibridge.settings.SettingsStore
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class PhoneAiEngine(private val modelStore: ModelStore, private val settingsStore: SettingsStore) : AiEngine {
    private val gguf = GgufLlamaAiEngine()
    private val requestMutex = Mutex()

    override suspend fun loadModel(modelPath: String): Boolean {
        val path = modelPath.ifBlank { modelStore.current().localPath }
        if (path.isBlank()) {
            modelStore.setError("No GGUF model selected")
            return false
        }
        modelStore.markLoading()
        val settings = settingsStore.read()
        return if (gguf.loadModel(path, settings.nCtx, settings.nThreads)) {
            modelStore.markLoaded()
            true
        } else {
            modelStore.setError(gguf.lastLoadError() ?: "GGUF model load failed")
            false
        }
    }

    override suspend fun isLoaded(): Boolean {
        val loaded = gguf.isLoaded()
        if (loaded && !modelStore.current().loaded) modelStore.markLoaded()
        return loaded
    }

    override suspend fun generate(prompt: String, maxTokens: Int): String {
        if (requestMutex.isLocked) throw AiBusyException()
        return requestMutex.withLock {
            val modelPath = modelStore.current().localPath
            if (modelPath.isBlank()) throw ModelNotReadyException("No GGUF model selected")

            modelStore.setBusy(true)
            try {
                if (!gguf.isLoaded() && !loadModel(modelPath)) {
                    throw ModelNotReadyException(modelStore.current().lastError ?: "GGUF model load failed")
                }
                val settings = settingsStore.read()
                runCatching {
                    gguf.generate(prompt, maxTokens.coerceAtMost(settings.maxTokens), settings.temperature)
                }.getOrElse {
                    modelStore.setError("GGUF generation failed: ${it.message ?: "unknown error"}")
                    throw it
                }
            } finally {
                modelStore.setBusy(false)
            }
        }
    }

    fun unloadModel() {
        gguf.unload()
        modelStore.markUnloaded()
    }
}

class ModelNotReadyException(message: String) : RuntimeException(message)
class AiBusyException : RuntimeException("AI engine is busy")
