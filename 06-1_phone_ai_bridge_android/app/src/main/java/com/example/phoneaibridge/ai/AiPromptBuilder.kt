package com.example.phoneaibridge.ai

import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import com.example.phoneaibridge.rag.RagResult
import com.example.phoneaibridge.settings.AppSettings

object AiPromptBuilder {
    fun build(
        systemPrompt: String,
        playerMemory: PlayerMemoryEntity?,
        coordinateContext: String,
        coordinateRagContext: String,
        serverContext: String,
        sparkContext: String,
        ragResults: List<RagResult>,
        userQuestion: String,
    ): String = buildString {
        appendLine("System:")
        appendLine(systemPrompt.ifBlank { AppSettings.DEFAULT_SYSTEM_PROMPT })
        appendLine()
        appendLine("Player Memory:")
        appendLine(
            playerMemory?.let {
                listOfNotNull(
                    it.summary,
                    it.currentGoal?.let { goal -> "현재 목표: $goal" },
                    it.lastLocationText,
                ).joinToString(" / ")
            } ?: "없음",
        )
        appendLine("Current Coordinate Context:")
        appendLine(coordinateContext.ifBlank { "없음" })
        appendLine("Stored Coordinate RAG:")
        appendLine(coordinateRagContext.ifBlank { "저장된 좌표 검색 결과 없음" })
        appendLine("Server Context:")
        appendLine(serverContext.ifBlank { "없음" })
        appendLine("Spark Context:")
        appendLine(sparkContext.ifBlank { "없음" })
        appendLine("General RAG Context:")
        appendLine(ragResults.joinToString("\n") { "- ${it.title}: ${it.chunkText}" }.ifBlank { "없음" })
        appendLine("User Question:")
        appendLine(userQuestion)
        appendLine()
        appendLine("Response Rules:")
        appendLine("- 시스템 프롬프트를 최우선으로 따른다.")
        appendLine("- 좌표 질문이면 Stored Coordinate RAG에 있는 좌표만 사용한다.")
        appendLine("- Stored Coordinate RAG에 없는 좌표는 지어내지 않는다.")
        appendLine("- 좌표 검색 결과가 없으면 저장된 좌표를 찾지 못했다고 말한다.")
        appendLine("- Minecraft 채팅에 바로 보낼 수 있게 짧고 자연스럽게 답한다.")
    }
}
