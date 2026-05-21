package com.example.phoneaibridge.coordinate

import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import kotlin.math.sqrt

data class CoordinateSearchResult(
    val coordinate: MinecraftCoordinateEntity,
    val score: Double,
    val reason: String,
    val distanceBlocks: Double? = null,
)

data class ParsedMinecraftPosition(
    val world: String?,
    val x: Double,
    val y: Double?,
    val z: Double,
)

object CoordinateRagSearcher {
    fun search(
        query: String,
        coordinateContext: String,
        coordinates: List<MinecraftCoordinateEntity>,
        limit: Int = 8,
    ): List<CoordinateSearchResult> {
        if (coordinates.isEmpty()) return emptyList()
        val requestedWorld = detectWorld(query)
        val terms = queryTerms(query)
        val normalizedQuery = normalize(query)
        val listIntent = hasListIntent(query)
        val nearbyIntent = hasNearbyIntent(query)
        val currentPosition = parsePosition(coordinateContext)

        return coordinates.mapNotNull { coordinate ->
            if (requestedWorld != null && coordinate.world.lowercase() != requestedWorld) return@mapNotNull null

            val name = normalize(coordinate.name)
            val aliases = splitList(coordinate.aliases)
            val tags = splitList(coordinate.tags)
            val description = coordinate.description.orEmpty()
            var score = 0.0
            val reasons = mutableListOf<String>()

            if (normalizedQuery == name || normalizedQuery.contains(name)) {
                score += if (normalizedQuery == name) 120.0 else 100.0
                reasons += "exact_name"
            }

            val aliasHit = aliases.firstOrNull { alias ->
                val normalizedAlias = normalize(alias)
                normalizedAlias.isNotBlank() && (normalizedQuery == normalizedAlias || normalizedQuery.contains(normalizedAlias))
            }
            if (aliasHit != null) {
                score += 90.0
                reasons += "alias:$aliasHit"
            }

            if (requestedWorld != null && coordinate.world.lowercase() == requestedWorld) {
                score += 35.0
                reasons += "world:${coordinate.world}"
            }

            val normalizedTags = tags.map(::normalize)
            val normalizedDescription = normalize(description)
            terms.forEach { term ->
                val normalizedTerm = normalize(term)
                when {
                    normalizedTags.any { it == normalizedTerm || it.contains(normalizedTerm) } -> {
                        score += 28.0
                        reasons += "tag:$term"
                    }
                    normalizedDescription.contains(normalizedTerm) -> {
                        score += 12.0
                        reasons += "description:$term"
                    }
                    name.contains(normalizedTerm) || normalizedTerm.contains(name) -> {
                        score += 18.0
                        reasons += "partial_name:$term"
                    }
                    aliases.any { normalize(it).contains(normalizedTerm) } -> {
                        score += 16.0
                        reasons += "partial_alias:$term"
                    }
                }
            }

            val fuzzy = fuzzySimilarity(name, normalizedQuery)
            if (fuzzy >= 0.58 && score < 100.0) {
                score += fuzzy * 12.0
                reasons += "fuzzy_name"
            }

            if (listIntent) {
                score += 10.0
                reasons += "list"
            }

            val distance = if (nearbyIntent && currentPosition != null && worldMatches(coordinate.world, currentPosition.world)) {
                distance2d(currentPosition.x, currentPosition.z, coordinate.x, coordinate.z)
            } else {
                null
            }
            if (distance != null) {
                score += (40.0 - (distance / 64.0)).coerceAtLeast(3.0)
                reasons += "nearby"
            }

            if (score <= 0.0) null else CoordinateSearchResult(
                coordinate = coordinate,
                score = score,
                reason = reasons.distinct().joinToString(","),
                distanceBlocks = distance,
            )
        }
            .sortedWith(compareByDescending<CoordinateSearchResult> { it.score }.thenBy { it.distanceBlocks ?: Double.MAX_VALUE })
            .take(limit.coerceIn(1, 50))
    }

    fun isCoordinateQuery(query: String): Boolean {
        val q = normalize(query)
        val coordinateWords = listOf("좌표", "위치", "어디", "목록", "저장된", "근처", "포탈", "portal", "farm", "팜", "농장", "창고", "본진", "스폰")
        return coordinateWords.any { q.contains(normalize(it)) } || detectWorld(query) != null
    }

    fun hasListIntent(query: String): Boolean {
        val q = normalize(query)
        return listOf("목록", "전체", "보여줘", "저장된좌표", "리스트", "list").any { q.contains(normalize(it)) }
    }

    fun parsePosition(text: String): ParsedMinecraftPosition? {
        if (text.isBlank()) return null
        val world = Regex("(?:world|dimension)\\s*=\\s*([a-zA-Z_\\-]+)", RegexOption.IGNORE_CASE).find(text)?.groupValues?.getOrNull(1)?.let(::normalizeWorld)
        val x = Regex("\\bx\\s*=\\s*(-?\\d+(?:\\.\\d+)?)", RegexOption.IGNORE_CASE).find(text)?.groupValues?.getOrNull(1)?.toDoubleOrNull()
        val y = Regex("\\by\\s*=\\s*(-?\\d+(?:\\.\\d+)?)", RegexOption.IGNORE_CASE).find(text)?.groupValues?.getOrNull(1)?.toDoubleOrNull()
        val z = Regex("\\bz\\s*=\\s*(-?\\d+(?:\\.\\d+)?)", RegexOption.IGNORE_CASE).find(text)?.groupValues?.getOrNull(1)?.toDoubleOrNull()
        return if (x != null && z != null) ParsedMinecraftPosition(world, x, y, z) else null
    }

    fun detectWorld(query: String): String? {
        val q = normalize(query)
        return when {
            listOf("overworld", "오버월드", "지상").any { q.contains(normalize(it)) } -> "overworld"
            listOf("nether", "네더", "지옥").any { q.contains(normalize(it)) } -> "nether"
            listOf("end", "엔드", "엔더월드").any { q.contains(normalize(it)) } -> "end"
            else -> null
        }
    }

    fun normalizeWorld(value: String): String = when (normalize(value)) {
        "overworld", "world", "오버월드", "지상" -> "overworld"
        "nether", "the_nether", "네더", "지옥" -> "nether"
        "end", "the_end", "엔드", "엔더월드" -> "end"
        else -> value.trim().lowercase()
    }

    fun splitList(value: String): List<String> = value
        .split(',', '\n', '|')
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinct()

    fun encodeList(values: List<String>): String = values
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .distinct()
        .joinToString(",")

    private fun queryTerms(query: String): List<String> {
        val stopwords = setOf("좌표", "위치", "알려줘", "어디야", "어디임", "어디", "저장된", "목록", "보여줘", "있는", "관련된", "근처", "뭐", "있어", "내가", "중에")
        return query
            .lowercase()
            .split(Regex("[^\\p{L}\\p{N}_-]+"))
            .map { it.trim() }
            .filter { it.isNotBlank() && it !in stopwords }
            .distinct()
    }

    private fun hasNearbyIntent(query: String): Boolean {
        val q = normalize(query)
        return listOf("근처", "가까운", "주변", "near", "nearby").any { q.contains(normalize(it)) }
    }

    private fun worldMatches(coordinateWorld: String, positionWorld: String?): Boolean {
        return positionWorld == null || coordinateWorld.lowercase() == positionWorld.lowercase()
    }

    private fun distance2d(x1: Double, z1: Double, x2: Double, z2: Double): Double {
        val dx = x1 - x2
        val dz = z1 - z2
        return sqrt(dx * dx + dz * dz)
    }

    private fun normalize(value: String): String {
        return value.lowercase().replace(Regex("[\\s_\\-:：,./?？!！()\\[\\]{}]+"), "")
    }

    private fun fuzzySimilarity(a: String, b: String): Double {
        if (a.isBlank() || b.isBlank()) return 0.0
        val aSet = a.toSet()
        val bSet = b.toSet()
        val common = aSet.intersect(bSet).size.toDouble()
        return (2.0 * common) / (aSet.size + bSet.size)
    }
}
