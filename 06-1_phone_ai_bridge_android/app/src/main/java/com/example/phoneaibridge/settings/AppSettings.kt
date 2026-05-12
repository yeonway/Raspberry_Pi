package com.example.phoneaibridge.settings

data class AppSettings(
    val port: Int = 8765,
    val apiToken: String = "",
    val modelPath: String = DEFAULT_GGUF_MODEL_PATH,
    val allowedRaspberryPiIp: String = "",
    val nCtx: Int = 2048,
    val nThreads: Int = 4,
    val maxTokens: Int = 256,
    val temperature: Float = 0.7f,
    val autoStartServer: Boolean = false,
    val autoLoadModel: Boolean = false,
    val keepAliveInBackground: Boolean = true,
    val systemPrompt: String = DEFAULT_SYSTEM_PROMPT,
) {
    companion object {
        const val DEFAULT_GGUF_MODEL_PATH = "/storage/emulated/0/Download/gemma-4-E4B-it-Q4_K_M.gguf"
        val DEFAULT_SYSTEM_PROMPT = """
너는 Minecraft 서버와 Raspberry Pi 환경에서 동작하는 로컬 AI 어시스턴트다.
답변은 짧고 실용적으로 한다.
좌표 정보가 없으면 지어내지 않는다.
서버 명령 실행, 블록 수정, 백업, 삭제 같은 작업을 실제로 수행한 것처럼 말하지 않는다.
모르는 내용은 추측하지 말고 모른다고 말한다.
""".trimIndent()
    }
}
