package com.example.phoneaibridge.ai

import com.example.phoneaibridge.rag.RagResult
import org.junit.Assert.assertTrue
import org.junit.Test

class AiPromptBuilderTest {
    @Test fun buildsStructuredPrompt() {
        val prompt = AiPromptBuilder.build(null, "철팜: overworld x=100 y=60 z=100", "TPS 20", "", listOf(RagResult("철팜", "주민과 침대 필요", 1.0)), "철팜 어디야?")
        assertTrue(prompt.contains("System:"))
        assertTrue(prompt.contains("Coordinate Context:"))
        assertTrue(prompt.contains("위험 명령"))
        assertTrue(prompt.contains("철팜 어디야?"))
    }
}
