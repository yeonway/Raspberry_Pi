package com.example.phoneaibridge.ai

class MockAiEngine : AiEngine {
    override suspend fun loadModel(modelPath: String): Boolean = true
    override suspend fun isLoaded(): Boolean = false

    override suspend fun generate(prompt: String, maxTokens: Int): String {
        val coordinate = prompt.lineAfterAny("Current Coordinate Context:", "Coordinate Context:")
        val memory = prompt.lineAfter("Player Memory:")
        val rag = prompt.lineAfterAny("Stored Coordinate RAG:", "General RAG Context:", "RAG Context:")
        val question = prompt.lineAfter("User Question:")
        return buildString {
            if (coordinate.isNotBlank() && coordinate != "없음") appendLine("현재 위치 정보: $coordinate")
            if (memory.isNotBlank() && memory != "없음") appendLine("기억 정보: $memory")
            if (rag.isNotBlank() && rag != "없음") appendLine("검색 정보: $rag")
            append(if (isBlank()) "Mock 응답입니다. 질문: $question" else "질문 '$question'에 대한 Mock 응답입니다.")
        }.trim().take(maxTokens.coerceAtLeast(40) * 6)
    }

    private fun String.lineAfter(label: String): String {
        return lineSequence().dropWhile { it.trim() != label }.drop(1).firstOrNull()?.trim().orEmpty()
    }

    private fun String.lineAfterAny(vararg labels: String): String {
        return labels.firstNotNullOfOrNull { label -> lineAfter(label).takeIf { it.isNotBlank() } }.orEmpty()
    }
}
