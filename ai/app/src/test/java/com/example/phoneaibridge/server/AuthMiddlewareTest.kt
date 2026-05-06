package com.example.phoneaibridge.server

import com.example.phoneaibridge.settings.AppSettings
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AuthMiddlewareTest {
    @Test fun healthDoesNotNeedToken() {
        assertTrue(AuthMiddleware.isAuthorized("/health", emptyMap(), null, AppSettings(apiToken = "secret")))
    }
    @Test fun apiNeedsToken() {
        assertFalse(AuthMiddleware.isAuthorized("/api/ask", emptyMap(), null, AppSettings(apiToken = "secret")))
        assertTrue(AuthMiddleware.isAuthorized("/api/ask", mapOf("x-api-token" to "secret"), null, AppSettings(apiToken = "secret")))
    }
    @Test fun optionalIpAllowListIsEnforced() {
        val settings = AppSettings(apiToken = "secret", allowedRaspberryPiIp = "192.168.0.10")
        assertFalse(AuthMiddleware.isAuthorized("/api/ask", mapOf("x-api-token" to "secret"), "192.168.0.11", settings))
        assertTrue(AuthMiddleware.isAuthorized("/api/ask", mapOf("x-api-token" to "secret"), "192.168.0.10", settings))
    }
}
