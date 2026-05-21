package com.example.phoneaibridge.model

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.time.OffsetDateTime

data class ModelSnapshot(
    val selected: Boolean = false,
    val name: String = "",
    val sizeBytes: Long = 0L,
    val localPath: String = "",
    val sourceUri: String = "",
    val copied: Boolean = false,
    val loaded: Boolean = false,
    val loading: Boolean = false,
    val copying: Boolean = false,
    val busy: Boolean = false,
    val lastLoadedAt: String = "",
    val lastMessage: String = "No model selected",
    val lastError: String? = null,
)

class ModelStore(private val context: Context) {
    private val prefs = context.getSharedPreferences("phone_ai_bridge_model", Context.MODE_PRIVATE)
    private val _snapshot = MutableStateFlow(readSnapshot())
    val snapshot: StateFlow<ModelSnapshot> = _snapshot

    fun current(): ModelSnapshot = _snapshot.value

    suspend fun copyModelFromUri(uri: Uri) = withContext(Dispatchers.IO) {
        setCopying(true, "Copying GGUF model...")
        runCatching {
            val metadata = queryMetadata(uri)
            require(metadata.name.endsWith(".gguf", ignoreCase = true)) { "Selected file is not a .gguf model" }

            val modelDir = File(context.filesDir, "models").also { it.mkdirs() }
            val target = File(modelDir, "selected.gguf")
            val temp = File(modelDir, "selected.gguf.tmp")

            context.contentResolver.openInputStream(uri).use { input ->
                requireNotNull(input) { "Unable to open selected model" }
                temp.outputStream().use { output -> input.copyTo(output) }
            }

            if (target.exists()) target.delete()
            require(temp.renameTo(target)) { "Unable to finalize copied model" }

            val size = target.length().takeIf { it > 0 } ?: metadata.sizeBytes
            prefs.edit()
                .putString(KEY_NAME, metadata.name)
                .putLong(KEY_SIZE, size)
                .putString(KEY_PATH, target.absolutePath)
                .putString(KEY_URI, uri.toString())
                .putBoolean(KEY_COPIED, true)
                .apply()

            _snapshot.value = readSnapshot().copy(lastMessage = "Model copied")
        }.getOrElse {
            setError(it.message ?: "Model copy failed")
        }
    }

    fun markLoading(message: String = "Loading model...") {
        _snapshot.value = _snapshot.value.copy(loading = true, lastMessage = message, lastError = null)
    }

    fun markLoaded() {
        _snapshot.value = _snapshot.value.copy(
            loaded = true,
            loading = false,
            lastLoadedAt = OffsetDateTime.now().toString(),
            lastMessage = "Model loaded",
            lastError = null,
        )
    }

    fun markUnloaded(message: String = "Model unloaded") {
        _snapshot.value = _snapshot.value.copy(loaded = false, loading = false, busy = false, lastMessage = message)
    }

    fun setBusy(busy: Boolean) {
        _snapshot.value = _snapshot.value.copy(busy = busy)
    }

    fun setError(message: String) {
        _snapshot.value = _snapshot.value.copy(loading = false, copying = false, busy = false, lastMessage = message, lastError = message)
    }

    fun clearModel() {
        val path = _snapshot.value.localPath
        if (path.isNotBlank()) runCatching { File(path).delete() }
        prefs.edit().clear().apply()
        _snapshot.value = readSnapshot()
    }

    private fun setCopying(copying: Boolean, message: String) {
        _snapshot.value = _snapshot.value.copy(copying = copying, lastMessage = message, lastError = null)
    }

    private fun readSnapshot(): ModelSnapshot {
        val path = prefs.getString(KEY_PATH, "").orEmpty()
        val name = prefs.getString(KEY_NAME, "").orEmpty()
        val copied = prefs.getBoolean(KEY_COPIED, false)
        val size = prefs.getLong(KEY_SIZE, 0L).takeIf { it > 0 } ?: path.takeIf { it.isNotBlank() }?.let { File(it).length() } ?: 0L
        val selected = path.isNotBlank() && File(path).isFile
        return ModelSnapshot(
            selected = selected,
            name = name,
            sizeBytes = size,
            localPath = path,
            sourceUri = prefs.getString(KEY_URI, "").orEmpty(),
            copied = copied && selected,
            lastMessage = if (selected) "Model ready to load" else "No model selected",
        )
    }

    private fun queryMetadata(uri: Uri): FileMetadata {
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

    private companion object {
        const val KEY_NAME = "name"
        const val KEY_SIZE = "size"
        const val KEY_PATH = "path"
        const val KEY_URI = "uri"
        const val KEY_COPIED = "copied"
    }
}
