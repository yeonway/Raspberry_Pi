package com.example.phoneaibridge.coordinate

import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoordinateRagSearcherTest {
    private val coordinates = listOf(
        MinecraftCoordinateEntity(name = "본진", aliases = "집,base", world = "overworld", x = 10.0, y = 64.0, z = -20.0, tags = "home,spawn", description = "처음 시작한 기지"),
        MinecraftCoordinateEntity(name = "네더 포탈", aliases = "포탈", world = "nether", x = 80.0, y = 70.0, z = 8.0, tags = "portal"),
        MinecraftCoordinateEntity(name = "철 농장", aliases = "철팜,iron farm", world = "overworld", x = 120.0, y = 64.0, z = 240.0, tags = "farm,iron"),
    )

    @Test
    fun exactNameBeatsGenericMatches() {
        val results = CoordinateRagSearcher.search("본진 좌표 알려줘", "", coordinates)
        assertEquals("본진", results.first().coordinate.name)
        assertTrue(results.first().reason.contains("exact_name"))
    }

    @Test
    fun aliasMatchFindsCoordinate() {
        val results = CoordinateRagSearcher.search("철팜 어디임?", "", coordinates)
        assertEquals("철 농장", results.first().coordinate.name)
        assertTrue(results.first().reason.contains("alias"))
    }

    @Test
    fun worldFilterLimitsResults() {
        val results = CoordinateRagSearcher.search("네더에 있는 포탈 알려줘", "", coordinates)
        assertEquals(1, results.size)
        assertEquals("nether", results.first().coordinate.world)
    }

    @Test
    fun nearbyUsesCurrentPositionWhenProvided() {
        val results = CoordinateRagSearcher.search("근처 좌표 뭐 있어?", "world=overworld x=12 y=64 z=-22", coordinates)
        assertEquals("본진", results.first().coordinate.name)
        assertTrue(results.first().distanceBlocks != null)
    }
}
