package com.example.phoneaibridge.ui

import android.app.Application
import android.content.Intent
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.phoneaibridge.Graph
import com.example.phoneaibridge.ai.AiBusyException
import com.example.phoneaibridge.ai.ModelNotReadyException
import com.example.phoneaibridge.ai.PhoneAiEngine
import com.example.phoneaibridge.settings.AppSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class ChatMessage(val role: String, val text: String)

data class HomeUiState(
    val isGenerating: Boolean = false,
    val isCopying: Boolean = false,
    val isLoading: Boolean = false,
    val modelSelected: Boolean = false,
    val modelLoaded: Boolean = false,
    val progressMessage: String = "",
    val errorMessage: String? = null,
    val healthResult: String = "",
    val settings: AppSettings = AppSettings(),
    val chatMessages: List<ChatMessage> = emptyList(),
)

class HomeViewModel(application: Application) : AndroidViewModel(application) {
    private val _uiState = MutableStateFlow(HomeUiState(settings = Graph.settings.read()))
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            Graph.modelStore.snapshot.collectLatest { model ->
                _uiState.update {
                    it.copy(
                        isCopying = model.copying,
                        isLoading = model.loading,
                        modelSelected = model.selected,
                        modelLoaded = model.loaded,
                        progressMessage = model.lastMessage,
                    )
                }
            }
        }
    }

    fun selectModel(uri: Uri) {
        copyModelToInternalStorage(uri)
    }

    fun copyModelToInternalStorage(uri: Uri) {
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    getApplication<Application>().contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    Graph.modelStore.copyModelFromUri(uri)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Graph.modelStore.setError("Model copy failed: ${e.message ?: "unknown error"}")
            }
        }
    }

    fun loadModel() {
        viewModelScope.launch {
            try {
                val path = Graph.modelStore.current().localPath
                if (path.isBlank()) {
                    Graph.modelStore.setError("No GGUF model selected")
                    return@launch
                }
                withContext(Dispatchers.IO) {
                    Graph.aiEngine.loadModel(path)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Graph.modelStore.setError("Model load failed: ${e.message ?: "unknown error"}")
            }
        }
    }

    fun unloadModel() {
        (Graph.aiEngine as? PhoneAiEngine)?.unloadModel()
    }

    fun generateGguf(message: String) {
        val question = message.trim()
        if (question.isBlank()) return
        if (_uiState.value.isGenerating || Graph.modelStore.current().busy) return

        if (!Graph.modelStore.current().selected) {
            _uiState.update {
                it.copy(
                    errorMessage = "모델이 선택되지 않았습니다.",
                    progressMessage = "No model selected",
                )
            }
            return
        }

        _uiState.update {
            it.copy(
                chatMessages = it.chatMessages + ChatMessage("You", question),
                isGenerating = true,
                errorMessage = null,
                progressMessage = "Generating...",
            )
        }

        viewModelScope.launch {
            try {
                val answer = withContext(Dispatchers.IO) {
                    Graph.aiEngine.generate(chatPrompt(question), Graph.settings.read().maxTokens)
                }
                _uiState.update {
                    it.copy(
                        isGenerating = false,
                        progressMessage = "Ready",
                        chatMessages = it.chatMessages + ChatMessage("AI", answer),
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                val messageText = userFacingError(e)
                _uiState.update {
                    it.copy(
                        isGenerating = false,
                        errorMessage = messageText,
                        progressMessage = messageText,
                    )
                }
            }
        }
    }

    fun clearChat() {
        _uiState.update { it.copy(chatMessages = emptyList(), errorMessage = null, progressMessage = "") }
    }

    fun testHealth() {
        viewModelScope.launch {
            try {
                val response = Graph.apiRoutes.handle("GET", "/health", emptyMap(), "", null).body
                com.example.phoneaibridge.server.ServerState.setHealthResult(response)
                _uiState.update { it.copy(healthResult = response, errorMessage = null) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _uiState.update { it.copy(errorMessage = "서버 상태 확인에 실패했습니다.") }
            }
        }
    }

    fun clearModel() {
        Graph.modelStore.clearModel()
    }

    fun updateSettings(settings: AppSettings) {
        Graph.settings.save(settings)
        _uiState.update { it.copy(settings = settings, progressMessage = "Settings saved") }
    }

    fun regenerateToken() {
        val token = Graph.settings.regenerateToken()
        val settings = Graph.settings.read().copy(apiToken = token)
        _uiState.update { it.copy(settings = settings, progressMessage = "Token regenerated") }
    }

    fun clearLogs() {
        viewModelScope.launch {
            try {
                Graph.aiRequestLogRepository.clearAll()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _uiState.update { it.copy(errorMessage = "Failed to clear logs: ${e.message ?: "unknown error"}") }
            }
        }
    }

    private fun chatPrompt(message: String): String = """
System:
${Graph.settings.read().systemPrompt.ifBlank { AppSettings.DEFAULT_SYSTEM_PROMPT }}

User:
$message
""".trimIndent()

    private fun userFacingError(error: Exception): String {
        val raw = error.message.orEmpty().lowercase()
        return when {
            error is ModelNotReadyException -> "모델이 선택되지 않았습니다."
            error is AiBusyException || "busy" in raw -> "AI가 다른 요청을 처리 중입니다."
            "timeout" in raw || "timed out" in raw -> "요청 시간이 초과되었습니다."
            "token" in raw || "unauthorized" in raw || "401" in raw -> "API Token이 올바르지 않습니다."
            "no gguf" in raw || "not loaded" in raw || "model" in raw && "selected" in raw -> "모델이 선택되지 않았습니다."
            else -> "AI 응답 생성에 실패했습니다."
        }
    }
}
