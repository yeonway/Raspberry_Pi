package com.example.phoneaibridge

import android.content.Context
import org.json.JSONObject
import kotlin.math.roundToInt

data class GeneratedAnswer(
    val answer: String,
    val usedRag: Boolean,
    val usedAi: Boolean,
    val model: String,
)

object AnswerGenerator {
    private data class ServerWorldContext(
        val name: String,
        val values: Map<String, String>,
    ) {
        val displayName: String
            get() = when (values["environment"]?.lowercase()) {
                "normal" -> "오버월드"
                "nether" -> "네더"
                "the_end" -> "엔드"
                else -> name
            }

        fun value(key: String): String? = values[key]?.takeIf { it.isNotBlank() }
    }

    fun generate(context: Context, payload: JSONObject): GeneratedAnswer {
        val message = payload.optString("message")
            .ifBlank { payload.optString("question") }
            .trim()
        val player = payload.optString("player_name")
            .ifBlank { payload.optString("player") }
            .ifBlank { "플레이어" }
        val rawCoordinateContext = payload.optString("coordinate_context")
        val serverContext = payload.optString("server_context")
        val coordinates = CoordinateStore.list(context)
        val matches = findCoordinateMatches(message, coordinates)
        val coordinateContext = buildCoordinateContext(
            savedCoordinates = coordinates,
            eventCoordinateContext = rawCoordinateContext,
        )
        val knowledgeMatches = KnowledgeStore.search(context, message)
        val localKnowledgeContext = knowledgeMatches.joinToString("\n") { "- ${it.toPromptText()}" }
        val knowledgeContext = listOf(localKnowledgeContext, payload.optString("knowledge_context"))
            .filter { it.isNotBlank() }
            .joinToString("\n")

        if (message.isBlank()) {
            return GeneratedAnswer(
                answer = "질문 내용이 비어 있습니다.",
                usedRag = false,
                usedAi = false,
                model = "none",
            )
        }

        if (looksCorrupted(message)) {
            return GeneratedAnswer(
                answer = "$player, 질문 글자가 깨져서 읽을 수 없습니다. 마인크래프트 채팅에서 다시 보내주세요.",
                usedRag = false,
                usedAi = false,
                model = "input-check",
            )
        }

        serverContextAnswer(message, player, serverContext, rawCoordinateContext)?.let { answer ->
            return GeneratedAnswer(
                answer = answer,
                usedRag = true,
                usedAi = false,
                model = "server-context",
            )
        }

        extractKnowledgeFileAnswer(message, knowledgeContext, player)?.let { answer ->
            return GeneratedAnswer(
                answer = answer,
                usedRag = true,
                usedAi = false,
                model = "knowledge-file",
            )
        }

        if (isCoordinateOnlyQuestion(message) && matches.isNotEmpty()) {
            return GeneratedAnswer(
                answer = "$player, 저장된 좌표에서 찾았습니다. " + matches.joinToString(" / ") { it.toAnswerText() },
                usedRag = true,
                usedAi = false,
                model = "coordinate-store",
            )
        }

        if (isKnowledgeLookupQuestion(message) && knowledgeContext.isNotBlank()) {
            return GeneratedAnswer(
                answer = "$player, 저장된 지식 기준입니다. " + compactRagAnswer(knowledgeContext),
                usedRag = true,
                usedAi = false,
                model = "knowledge-store",
            )
        }

        if (knowledgeContext.isBlank()) ruleBasedAnswer(message, player)?.let { answer ->
            return GeneratedAnswer(
                answer = answer,
                usedRag = false,
                usedAi = false,
                model = "phone-minecraft-rules",
            )
        }

        val prompt = buildPrompt(
            player = player,
            question = message,
            coordinateContext = coordinateContext,
            knowledgeContext = knowledgeContext,
            serverContext = serverContext,
            sparkContext = payload.optString("spark_context"),
            systemPrompt = payload.optString("system_prompt"),
        )

        return runCatching {
            val raw = PhoneLlamaEngine.generate(prompt, payload.optInt("max_tokens", 160))
            GeneratedAnswer(
                answer = cleanAnswer(raw),
                usedRag = coordinateContext.isNotBlank() || knowledgeContext.isNotBlank(),
                usedAi = true,
                model = PhoneLlamaEngine.snapshot(context).optString("engine", "phone-llama.cpp"),
            )
        }.getOrElse { error ->
            GeneratedAnswer(
                answer = "$player, 폰 AI 모델을 먼저 로드해야 합니다. 앱에서 GGUF 모델 선택 후 모델 로드를 눌러주세요. (${error.message ?: "unknown error"})",
                usedRag = false,
                usedAi = false,
                model = "phone-llama.cpp",
            )
        }
    }

    private fun buildPrompt(
        player: String,
        question: String,
        coordinateContext: String,
        knowledgeContext: String,
        serverContext: String,
        sparkContext: String,
        systemPrompt: String,
    ): String {
        val system = systemPrompt.trim().ifBlank { defaultSystemPrompt() }
        val user = buildString {
        appendLine("플레이어: $player")
        if (knowledgeContext.isNotBlank()) {
            appendLine("저장된 지식:")
            appendLine(knowledgeContext)
        }
        if (coordinateContext.isNotBlank()) {
            appendLine("저장된 좌표:")
            appendLine(coordinateContext)
        }
        if (serverContext.isNotBlank()) {
            appendLine("서버 상황:")
            appendLine(serverContext)
        }
        if (sparkContext.isNotBlank()) {
            appendLine("성능 상황:")
            appendLine(sparkContext)
        }
        appendLine("질문:")
        appendLine(question)
        appendLine("한국어 답변만 출력:")
        }
        return "<|im_start|>system\n$system<|im_end|>\n<|im_start|>user\n$user<|im_end|>\n<|im_start|>assistant\n"
    }

    private fun defaultSystemPrompt(): String = buildString {
        appendLine("너는 Minecraft Java/Paper 서버 도우미다.")
        appendLine("반드시 한국어로만 답한다.")
        appendLine("답변은 1~3문장으로 짧게 한다.")
        appendLine("서바이벌 멀티플레이 기준으로 실용적으로 답한다.")
        appendLine("저장된 지식이 질문과 관련 있으면 일반 지식보다 우선한다.")
        appendLine("저장된 좌표가 관련 있으면 그 좌표를 사용한다.")
        appendLine("난이도, 날씨, 시간, 접속자, TPS, 게임모드 질문은 서버 상황 값을 우선 사용한다.")
        appendLine("모델, 브리지, 앱이라는 말은 하지 않는다.")
        appendLine()
        appendLine("기본 정보:")
        appendLine("- 다이아몬드는 최신 버전에서 보통 Y=-59 근처가 좋다.")
        appendLine("- 철은 Y=16 근처 또는 높은 산에서 잘 나온다.")
        appendLine("- 네더라이트 고대 잔해는 보통 Y=15 근처가 좋다.")
        appendLine("- 이 서버는 한 명만 자도 밤을 넘길 수 있다.")
        appendLine("- Paper Anti-Xray가 켜져 있다.")
    }.trim()

    private fun cleanAnswer(raw: String): String {
        return raw
            .substringBefore("System:")
            .substringBefore("Question:")
            .substringBefore("Player:")
            .substringBefore("Korean answer:")
            .replace("<|im_end|>", "")
            .replace("<|im_start|>assistant", "")
            .replace(Regex("(?i)^player\\s*:\\s*[^,]+,?\\s*"), "")
            .replace(Regex("^플레이어\\s*:\\s*[^,]+,?\\s*"), "")
            .trim()
            .ifBlank { raw.trim() }
    }

    private fun buildCoordinateContext(
        savedCoordinates: List<SavedCoordinate>,
        eventCoordinateContext: String,
    ): String {
        return buildString {
            if (savedCoordinates.isNotEmpty()) {
                appendLine("저장 좌표:")
                savedCoordinates.take(20).forEach { appendLine("- ${it.toAnswerText()}") }
            }
            if (eventCoordinateContext.isNotBlank()) {
                appendLine("현재 플레이어 좌표:")
                appendLine(eventCoordinateContext)
            }
        }.trim()
    }

    private fun extractKnowledgeFileAnswer(message: String, knowledgeContext: String, player: String): String? {
        if (!message.contains(".md", ignoreCase = true) && !message.contains(".txt", ignoreCase = true)) {
            return null
        }
        if (!knowledgeContext.contains("FILE:") || !knowledgeContext.contains("CONTENT:")) {
            return null
        }

        val blocks = knowledgeContext.split(Regex("\\n\\n(?=FILE: )"))
        val rendered = blocks.mapNotNull { block ->
            val filename = block.lineSequence()
                .firstOrNull { it.startsWith("FILE:") }
                ?.substringAfter("FILE:")
                ?.trim()
                .orEmpty()
            val marker = "\nCONTENT:\n"
            val contentStart = block.indexOf(marker)
            if (filename.isBlank() || contentStart < 0) {
                null
            } else {
                val content = block.substring(contentStart + marker.length).trim()
                if (content.isBlank()) null else "[$filename]\n$content"
            }
        }
        if (rendered.isEmpty()) {
            return null
        }

        return "$player, 파일 내용입니다.\n" + rendered.joinToString("\n\n").take(3500)
    }

    private fun isCoordinateOnlyQuestion(message: String): Boolean {
        return message.contains("좌표") || message.contains("어디") || message.contains("위치")
    }

    private fun isKnowledgeLookupQuestion(message: String): Boolean {
        return message.contains("뭐") ||
            message.contains("알려") ||
            message.contains("규칙") ||
            message.contains("지식") ||
            message.contains("설명") ||
            message.contains("기억")
    }

    private fun compactRagAnswer(context: String): String {
        return context
            .lineSequence()
            .map { it.trim().removePrefix("-").trim() }
            .filter { it.isNotBlank() }
            .take(3)
            .joinToString(" / ")
            .take(1200)
    }

    private fun serverContextAnswer(
        message: String,
        player: String,
        serverContext: String,
        coordinateContext: String,
    ): String? {
        if (serverContext.isBlank()) return null

        val lowered = message.lowercase()
        if (!isServerContextQuestion(lowered)) return null

        val worlds = parseWorldContexts(serverContext)
        val currentWorldName = Regex("""world=([^\s;]+)""")
            .find(coordinateContext)
            ?.groupValues
            ?.get(1)
        val world = worlds.firstOrNull { it.name.equals(currentWorldName, ignoreCase = true) }
            ?: worlds.firstOrNull()
        val asksSummary = lowered.contains("상태") || lowered.contains("정보") || lowered.contains("설정")
        val asksAllWorlds = lowered.contains("월드별") || lowered.contains("모든 월드") || lowered.contains("각 월드")
        val parts = mutableListOf<String>()

        if (asksSummary || lowered.contains("접속") || lowered.contains("온라인") || lowered.contains("몇 명") || lowered.contains("몇명") || lowered.contains("인원")) {
            serverValue(serverContext, "online_players")?.let { online ->
                val names = serverValue(serverContext, "online_player_names")
                    ?.takeUnless { it.equals("none", ignoreCase = true) }
                    ?.replace(",", ", ")
                parts += if (names.isNullOrBlank()) {
                    "접속 인원은 ${online}입니다"
                } else {
                    "접속 인원은 ${online}이고, 접속자는 ${names}입니다"
                }
            }
        }

        if (!asksAllWorlds && (asksSummary || lowered.contains("난이도") || lowered.contains("difficulty"))) {
            world?.value("difficulty")?.let { parts += "${world.displayName} 난이도는 ${koreanDifficulty(it)}입니다" }
        }

        if (asksSummary || lowered.contains("게임모드") || lowered.contains("gamemode")) {
            val currentGameMode = Regex("""gamemode=([^\s;]+)""")
                .find(coordinateContext)
                ?.groupValues
                ?.get(1)
            val defaultGameMode = serverValue(serverContext, "default_gamemode")
            when {
                !currentGameMode.isNullOrBlank() -> parts += "현재 게임모드는 ${koreanGameMode(currentGameMode)}입니다"
                !defaultGameMode.isNullOrBlank() -> parts += "기본 게임모드는 ${koreanGameMode(defaultGameMode)}입니다"
            }
        }

        if (!asksAllWorlds && (asksSummary || lowered.contains("날씨") || lowered.contains("비") || lowered.contains("천둥"))) {
            world?.value("weather")?.let { parts += "${world.displayName} 날씨는 ${koreanWeather(it)}입니다" }
        }

        if (!asksAllWorlds && (asksSummary || lowered.contains("시간") || lowered.contains("낮") || lowered.contains("밤"))) {
            world?.let {
                val period = it.value("time_period")?.let(::koreanTimePeriod)
                val ticks = it.value("time")
                if (!period.isNullOrBlank() && !ticks.isNullOrBlank()) {
                    parts += "${it.displayName} 시간은 $period(${ticks}틱)입니다"
                } else if (!period.isNullOrBlank()) {
                    parts += "${it.displayName} 시간은 ${period}입니다"
                }
            }
        }

        if (asksSummary || lowered.contains("tps") || lowered.contains("렉") || lowered.contains("성능")) {
            serverValue(serverContext, "tps_1m_5m_15m")?.let { parts += "TPS는 ${it}입니다" }
        }

        if (!asksAllWorlds && (lowered.contains("pvp") || lowered.contains("피브이피"))) {
            world?.value("pvp")?.let { parts += "PVP는 ${if (it.equals("true", ignoreCase = true)) "켜져 있습니다" else "꺼져 있습니다"}" }
        }

        if (lowered.contains("화이트리스트") || lowered.contains("whitelist")) {
            serverValue(serverContext, "whitelist")?.let { parts += "화이트리스트는 ${if (it.equals("true", ignoreCase = true)) "켜져 있습니다" else "꺼져 있습니다"}" }
        }

        if (lowered.contains("정품") || lowered.contains("온라인 모드") || lowered.contains("online mode") || lowered.contains("online-mode")) {
            serverValue(serverContext, "online_mode")?.let { parts += "온라인 모드는 ${if (it.equals("true", ignoreCase = true)) "켜져 있습니다" else "꺼져 있습니다"}" }
        }

        if (!asksAllWorlds && (lowered.contains("스폰") || lowered.contains("spawn"))) {
            world?.let {
                val x = it.value("spawn_x")
                val y = it.value("spawn_y")
                val z = it.value("spawn_z")
                if (!x.isNullOrBlank() && !y.isNullOrBlank() && !z.isNullOrBlank()) {
                    parts += "${it.displayName} 스폰은 x=$x y=$y z=${z}입니다"
                }
            }
        }

        if (asksAllWorlds) {
            worldSummary(worlds).takeIf { it.isNotBlank() }?.let { parts += it }
        }

        if (parts.isEmpty()) return null
        return "$player, ${parts.joinToString(" ")}"
    }

    private fun isServerContextQuestion(lowered: String): Boolean {
        return listOf(
            "난이도",
            "difficulty",
            "서버 상태",
            "서버 정보",
            "서버 설정",
            "접속",
            "온라인",
            "몇 명",
            "몇명",
            "인원",
            "tps",
            "렉",
            "성능",
            "날씨",
            "비",
            "천둥",
            "시간",
            "낮",
            "밤",
            "게임모드",
            "gamemode",
            "화이트리스트",
            "whitelist",
            "정품",
            "online mode",
            "online-mode",
            "pvp",
            "피브이피",
            "스폰",
            "spawn",
        ).any { lowered.contains(it) }
    }

    private fun parseWorldContexts(serverContext: String): List<ServerWorldContext> {
        val worldsValue = serverContext.substringAfter("worlds=", "")
        if (worldsValue.isBlank() || worldsValue == "none") return emptyList()

        return Regex("""([^{}\s|]+)\{([^{}]+)\}""")
            .findAll(worldsValue)
            .map { match ->
                val name = match.groupValues[1]
                val values = match.groupValues[2]
                    .split(",")
                    .mapNotNull { token ->
                        val index = token.indexOf('=')
                        if (index <= 0) {
                            null
                        } else {
                            token.substring(0, index).trim() to token.substring(index + 1).trim()
                        }
                    }
                    .toMap()
                ServerWorldContext(name, values)
            }
            .toList()
    }

    private fun worldSummary(worlds: List<ServerWorldContext>): String {
        if (worlds.isEmpty()) return ""

        return "월드별 정보는 " + worlds.joinToString("; ") { world ->
            val difficulty = world.value("difficulty")?.let(::koreanDifficulty)?.let { "난이도 $it" }
            val period = world.value("time_period")?.let(::koreanTimePeriod)
            val ticks = world.value("time")
            val time = when {
                !period.isNullOrBlank() && !ticks.isNullOrBlank() -> "시간 $period(${ticks}틱)"
                !period.isNullOrBlank() -> "시간 $period"
                else -> null
            }
            val weather = world.value("weather")?.let(::koreanWeather)?.let { "날씨 $it" }
            val pvp = world.value("pvp")?.let { "PVP ${if (it.equals("true", ignoreCase = true)) "켜짐" else "꺼짐"}" }
            val x = world.value("spawn_x")
            val y = world.value("spawn_y")
            val z = world.value("spawn_z")
            val spawn = if (!x.isNullOrBlank() && !y.isNullOrBlank() && !z.isNullOrBlank()) {
                "스폰 x=$x y=$y z=$z"
            } else {
                null
            }
            val details = listOfNotNull(difficulty, time, weather, pvp, spawn).joinToString(", ")
            "${world.displayName}($details)"
        } + "입니다"
    }

    private fun serverValue(serverContext: String, key: String): String? {
        val pattern = "(?:^|;\\s*)${Regex.escape(key)}=([^;]+)"
        return Regex(pattern)
            .find(serverContext)
            ?.groupValues
            ?.get(1)
            ?.trim()
            ?.takeIf { it.isNotBlank() }
    }

    private fun koreanDifficulty(value: String): String = when (value.lowercase()) {
        "peaceful" -> "평화로움"
        "easy" -> "쉬움"
        "normal" -> "보통"
        "hard" -> "어려움"
        else -> value
    }

    private fun koreanGameMode(value: String): String = when (value.lowercase()) {
        "survival" -> "서바이벌"
        "creative" -> "크리에이티브"
        "adventure" -> "모험"
        "spectator" -> "관전자"
        else -> value
    }

    private fun koreanWeather(value: String): String = when (value.lowercase()) {
        "clear" -> "맑음"
        "rain" -> "비"
        "thunder" -> "천둥"
        else -> value
    }

    private fun koreanTimePeriod(value: String): String = when (value.lowercase()) {
        "dawn" -> "새벽"
        "day" -> "낮"
        "dusk" -> "해질녘"
        "night" -> "밤"
        else -> value
    }

    private fun ruleBasedAnswer(message: String, player: String): String? {
        val lowered = message.lowercase()
        return when {
            lowered == "안녕" || lowered == "안녕하세요" || lowered == "하이" || lowered == "hi" || lowered == "hello" -> {
                "$player, 안녕하세요. 마크에서 궁금한 거 있으면 바로 물어보세요."
            }
            lowered.contains("네더라이트") || lowered.contains("고대 잔해") || lowered.contains("netherite") -> {
                "$player, 네더라이트용 고대 잔해는 네더에서 Y=15 근처를 파는 게 좋습니다. 침대 폭발을 쓸 때는 화염 저항과 대피 공간을 챙기세요."
            }
            lowered.contains("다이아") || lowered.contains("diamond") -> {
                "$player, 다이아몬드는 최신 버전 기준 Y=-59 근처에서 브랜치마이닝하는 게 좋습니다."
            }
            lowered.contains("철") || lowered.contains("iron") -> {
                "$player, 철은 Y=16 근처나 높은 산 지형에서 잘 나옵니다."
            }
            lowered.contains("침대") || lowered.contains("잠") || lowered.contains("sleep") -> {
                "$player, 이 서버는 여러 명이 있어도 한 명만 자면 밤을 넘길 수 있습니다."
            }
            lowered.contains("엑스레이") || lowered.contains("xray") || lowered.contains("x-ray") -> {
                "$player, 이 서버는 Paper Anti-Xray가 켜져 있어서 광물 엑스레이가 잘 통하지 않습니다."
            }
            else -> null
        }
    }

    private fun looksCorrupted(message: String): Boolean {
        val questionMarks = message.count { it == '?' }
        return message.length >= 6 && questionMarks >= 3 && questionMarks * 2 >= message.length
    }

    private fun findCoordinateMatches(message: String, coordinates: List<SavedCoordinate>): List<SavedCoordinate> {
        val words = message
            .lowercase()
            .split(Regex("\\s+"))
            .map { it.trim { char -> !char.isLetterOrDigit() && char != '_' && char != '-' } }
            .filter { it.length >= 2 }
        if (words.isEmpty()) return emptyList()

        return coordinates
            .filter { coordinate ->
                val text = coordinate.searchText()
                words.any { word -> text.contains(word) }
            }
            .take(3)
    }

    private fun SavedCoordinate.toAnswerText(): String {
        val yText = y?.let { " y=${it.roundText()}" }.orEmpty()
        val note = description.takeIf { it.isNotBlank() }?.let { " ($it)" }.orEmpty()
        return "$name [$world] x=${x.roundText()}$yText z=${z.roundText()}$note"
    }

    private fun Double.roundText(): String {
        return if (this == roundToInt().toDouble()) roundToInt().toString() else "%.1f".format(this)
    }
}
