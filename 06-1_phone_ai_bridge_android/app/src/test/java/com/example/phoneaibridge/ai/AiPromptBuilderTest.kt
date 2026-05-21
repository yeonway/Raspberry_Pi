package com.example.phoneaibridge.ai

import com.example.phoneaibridge.rag.RagResult
import org.junit.Assert.assertTrue
import org.junit.Test

class AiPromptBuilderTest {
    @Test
    fun buildsStructuredPrompt() {
        val prompt = AiPromptBuilder.build(
            systemPrompt = "테스트 시스템 프롬프트",
            playerMemory = null,
            coordinateContext = "좌표: overworld x=100 y=60 z=100",
            coordinateRagContext = "name=철팜, world=overworld, x=100, y=64, z=100",
            serverContext = "TPS 20",
            sparkContext = "",
            ragResults = listOf(RagResult("철팜", "주변에 침대가 필요", 1.0)),
            userQuestion = "철팜 어디야?",
        )

        assertTrue(prompt.contains("System:"))
        assertTrue(prompt.contains("테스트 시스템 프롬프트"))
        assertTrue(prompt.contains("Current Coordinate Context:"))
        assertTrue(prompt.contains("Stored Coordinate RAG:"))
        assertTrue(prompt.contains("철팜 어디야?"))
    }
}
