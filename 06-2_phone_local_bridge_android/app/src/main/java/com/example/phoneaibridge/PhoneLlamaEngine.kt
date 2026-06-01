package com.example.phoneaibridge

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import com.example.phoneaibridge.ai.LlamaNative
import org.json.JSONObject
import java.io.File
import java.time.OffsetDateTime

object PhoneLlamaEngine {
    private const val PREFS_NAME = "phone_llama_engine"
    private const val KEY_MODEL_NAME = "model_name"
    private const val KEY_MODEL_PATH = "model_path"
    private const val MIN_GGUF_BYTES = 1024L * 1024L

    private val lock = Any()
    private val nativeLock = Any()

    @Volatile private var handle: Long = 0L
    @Volatile private var loadedPath: String = ""
    @Volatile private var loading: Boolean = false
    @Volatile private var generating: Boolean = false
    @Volatile private var lastMessage: String = "모델을 선택하세요"
    @Volatile private var lastError: String = ""

    fun copyModelFromUri(context: Context, uri: Uri): Boolean {
        synchronized(lock) {
            loading = true
            lastMessage = "모델 복사 중"
            lastError = ""
        }

        return runCatching {
            val metadata = queryMetadata(context, uri)
            require(metadata.name.endsWith(".gguf", ignoreCase = true)) { "GGUF 파일을 선택해야 합니다" }

            val modelDir = File(context.filesDir, "models").also { it.mkdirs() }
            val target = File(modelDir, "selected.gguf")
            val temp = File(modelDir, "selected.gguf.tmp")

            context.contentResolver.openInputStream(uri).use { input ->
                requireNotNull(input) { "선택한 모델을 열 수 없습니다" }
                temp.outputStream().use { output -> input.copyTo(output) }
            }

            if (target.exists()) target.delete()
            require(temp.renameTo(target)) { "모델 복사를 완료하지 못했습니다" }
            require(target.length() >= MIN_GGUF_BYTES) { "모델 파일이 너무 작습니다" }

            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_MODEL_NAME, metadata.name)
                .putString(KEY_MODEL_PATH, target.absolutePath)
                .apply()

            synchronized(lock) {
                lastMessage = "모델 복사 완료"
                lastError = ""
                loading = false
            }
            true
        }.getOrElse { error ->
            synchronized(lock) {
                loading = false
                lastMessage = "모델 복사 실패"
                lastError = error.message ?: "unknown error"
            }
            false
        }
    }

    @Synchronized
    fun loadSelectedModel(context: Context): Boolean {
        val path = selectedModelPath(context)
        synchronized(lock) {
            loading = true
            lastMessage = "모델 로드 중"
            lastError = ""
        }

        return runCatching {
            require(path.isNotBlank()) { "선택된 모델이 없습니다" }
            val file = File(path)
            require(file.isFile) { "모델 파일이 없습니다: $path" }
            require(file.length() >= MIN_GGUF_BYTES) { "모델 파일이 너무 작습니다" }

            val alreadyLoaded = handle != 0L && loadedPath == path
            if (alreadyLoaded) {
                synchronized(lock) {
                    loading = false
                    lastMessage = "모델 이미 로드됨"
                }
                return true
            }

            synchronized(nativeLock) {
                val oldHandle = handle
                if (oldHandle != 0L) {
                    LlamaNative.freeModel(oldHandle)
                }
                handle = 0L
                loadedPath = ""
            }

            val newHandle = LlamaNative.loadModel(path, 2048, Runtime.getRuntime().availableProcessors().coerceIn(2, 6))
            synchronized(lock) {
                handle = newHandle
                loadedPath = path
                loading = false
                lastMessage = "모델 로드 완료"
                lastError = ""
            }
            true
        }.getOrElse { error ->
            synchronized(lock) {
                handle = 0L
                loadedPath = ""
                loading = false
                lastMessage = "모델 로드 실패"
                lastError = error.message ?: "unknown error"
            }
            false
        }
    }

    fun unload() {
        synchronized(nativeLock) {
            val oldHandle = handle
            if (oldHandle != 0L) {
                LlamaNative.freeModel(oldHandle)
            }
            handle = 0L
            loadedPath = ""
        }
        synchronized(lock) {
            lastMessage = "모델 언로드됨"
        }
    }

    fun isLoaded(): Boolean {
        return handle != 0L
    }

    fun generate(prompt: String, maxTokens: Int): String {
        val current = handle
        synchronized(lock) {
            require(current != 0L) { "폰 AI 모델이 로드되지 않았습니다. 앱에서 GGUF 모델을 선택하고 로드하세요." }
            generating = true
            lastMessage = "답변 생성 중"
        }

        return try {
            val answer = synchronized(nativeLock) {
                LlamaNative.generate(
                    handle = current,
                    prompt = prompt,
                    maxTokens = maxTokens.coerceIn(16, 768),
                    temperature = 0.45f,
                    topK = 40,
                    topP = 0.9f,
                )
            }.trim()
            synchronized(lock) {
                lastMessage = "답변 생성 완료"
                lastError = ""
            }
            answer
        } catch (error: Throwable) {
            synchronized(lock) {
                lastMessage = "답변 생성 실패"
                lastError = error.message ?: "unknown error"
            }
            throw error
        } finally {
            synchronized(lock) {
                generating = false
            }
        }
    }

    fun snapshot(context: Context): JSONObject {
        val path = selectedModelPath(context)
        val file = path.takeIf { it.isNotBlank() }?.let { File(it) }
        return JSONObject()
            .put("selected", file?.isFile == true)
            .put("loaded", isLoaded())
            .put("loading", loading)
            .put("generating", generating)
            .put("modelName", selectedModelName(context))
            .put("modelPath", path)
            .put("modelSizeBytes", file?.length() ?: 0L)
            .put("engine", "phone-llama.cpp")
            .put("lastMessage", lastMessage)
            .put("lastError", lastError)
            .put("time", OffsetDateTime.now().toString())
    }

    private fun selectedModelPath(context: Context): String {
        val saved = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_MODEL_PATH, "")
            .orEmpty()
        if (saved.isNotBlank()) return saved
        return File(File(context.filesDir, "models"), "selected.gguf")
            .takeIf { it.isFile }
            ?.absolutePath
            .orEmpty()
    }

    private fun selectedModelName(context: Context): String {
        val saved = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_MODEL_NAME, "")
            .orEmpty()
        if (saved.isNotBlank()) return saved
        return File(File(context.filesDir, "models"), "selected.gguf")
            .takeIf { it.isFile }
            ?.name
            .orEmpty()
    }

    private fun queryMetadata(context: Context, uri: Uri): FileMetadata {
        var name = "selected.gguf"
        var size = -1L
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
            if (cursor.moveToFirst()) {
                if (nameIndex >= 0) name = cursor.getString(nameIndex) ?: name
                if (sizeIndex >= 0) size = cursor.getLong(sizeIndex)
            }
        }
        return FileMetadata(name, size)
    }

    private data class FileMetadata(val name: String, val sizeBytes: Long)
}
