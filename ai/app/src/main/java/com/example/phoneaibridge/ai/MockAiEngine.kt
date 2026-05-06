package com.example.phoneaibridge.ai

class MockAiEngine : AiEngine {
    override suspend fun loadModel(modelPath: String): Boolean = true
    override suspend fun isLoaded(): Boolean = false
    override suspend fun generate(prompt: String, maxTokens: Int): String {
        val coordinate = prompt.lineAfter("Coordinate Context:")
        val memory = prompt.lineAfter("Player Memory:")
        val rag = prompt.lineAfter("RAG Context:")
        val question = prompt.lineAfter("User Question:")
        return buildString {
            if (coordinate.isNotBlank()) appendLine("요청한 위치 정보는 $coordinate 입니다.")
            if (memory.isNotBlank() && memory != "없음") appendLine("기억상황을 보면 $memory")
            if (rag.isNotBlank() && rag != "없음") appendLine("관련 지식: $rag")
            append(if (isBlank()) "현재 MockAiEngine이라 실제 추론 대신 질문을 정리해 답합니다: $question" else "질문 '$question'에 대한 MVP Mock 응답입니다.")
        }.trim().take(maxTokens.coerceAtLeast(40) * 6)
    }
    private fun String.lineAfter(label: String): String = lineSequence().dropWhile { it.trim() != label }.drop(1).firstOrNull()?.trim().orEmpty()
}
