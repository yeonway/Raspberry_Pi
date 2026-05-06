package com.example.phoneaibridge.ai

import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import com.example.phoneaibridge.rag.RagResult

object AiPromptBuilder {
    fun build(
        playerMemory: PlayerMemoryEntity?,
        coordinateContext: String,
        serverContext: String,
        sparkContext: String,
        ragResults: List<RagResult>,
        userQuestion: String,
    ): String = buildString {
        appendLine("System:")
        appendLine("너는 Minecraft 서버용 AI 도우미다.")
        appendLine("위험 명령 실행, 블록 수정, 백업/삭제 명령 실행은 절대 하지 않는다.")
        appendLine("짧고 명확하게 한국어로 답변한다.")
        appendLine()
        appendLine("Player Memory:")
        appendLine(playerMemory?.let { listOfNotNull(it.summary, it.currentGoal?.let { goal -> "현재 목표: $goal" }, it.lastLocationText).joinToString(" / ") } ?: "없음")
        appendLine("Coordinate Context:")
        appendLine(coordinateContext.ifBlank { "없음" })
        appendLine("Server Context:")
        appendLine(serverContext.ifBlank { "없음" })
        appendLine("Spark Context:")
        appendLine(sparkContext.ifBlank { "없음" })
        appendLine("RAG Context:")
        appendLine(ragResults.joinToString("\n") { "- ${it.title}: ${it.chunkText}" }.ifBlank { "없음" })
        appendLine("User Question:")
        appendLine(userQuestion)
        appendLine("Response Rules: 3~8줄, 좌표는 정확히 표시, 모르면 모른다고 말하기, 위험 명령 제안 금지.")
    }
}
