package com.example.phoneaibridge.server

import com.example.phoneaibridge.settings.AppSettings

object AuthMiddleware {
    fun isAuthorized(path: String, headers: Map<String, String>, remoteIp: String?, settings: AppSettings): Boolean {
        if (!path.startsWith("/api/")) return true
        val allowedIp = settings.allowedRaspberryPiIp.trim()
        if (allowedIp.isNotEmpty() && remoteIp != allowedIp) return false
        return headers["x-api-token"] == settings.apiToken
    }
}
