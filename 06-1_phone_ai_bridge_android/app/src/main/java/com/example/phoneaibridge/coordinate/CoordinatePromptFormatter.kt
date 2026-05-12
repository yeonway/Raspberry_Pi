package com.example.phoneaibridge.coordinate

import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity

object CoordinatePromptFormatter {
    fun format(results: List<CoordinateSearchResult>, coordinateQuery: Boolean): String {
        if (results.isEmpty()) {
            return if (coordinateQuery) {
                "좌표 질문으로 판단했지만 저장된 좌표에서 일치하는 항목을 찾지 못함. 좌표를 지어내지 말 것."
            } else {
                "좌표 검색 결과 없음."
            }
        }

        return buildString {
            appendLine("저장된 좌표 검색 결과:")
            results.forEachIndexed { index, result ->
                appendLine("${index + 1}. ${result.coordinate.toPromptLine()} / match=${result.reason} / score=${"%.1f".format(result.score)}")
                result.distanceBlocks?.let { appendLine("   현재 위치와 거리: ${"%.1f".format(it)} blocks") }
            }
            appendLine("주의: 위 목록에 없는 좌표는 모른다고 답하고, 임의 좌표를 만들지 않는다.")
        }.trim()
    }

    fun MinecraftCoordinateEntity.toPromptLine(): String {
        val yText = y?.let { ", y=${formatNumber(it)}" } ?: ""
        val aliasText = aliases.takeIf { it.isNotBlank() }?.let { ", aliases=[$it]" }.orEmpty()
        val tagText = tags.takeIf { it.isNotBlank() }?.let { ", tags=[$it]" }.orEmpty()
        val descriptionText = description?.takeIf { it.isNotBlank() }?.let { ", memo=$it" }.orEmpty()
        return "name=$name, world=$world, x=${formatNumber(x)}$yText, z=${formatNumber(z)}$aliasText$tagText$descriptionText"
    }

    private fun formatNumber(value: Double): String {
        return if (value % 1.0 == 0.0) value.toLong().toString() else "%.2f".format(value)
    }
}
