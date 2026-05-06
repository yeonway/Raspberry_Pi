package com.example.phoneaibridge.settings

data class AppSettings(val port: Int = 8765, val apiToken: String = "", val modelPath: String = "", val allowedRaspberryPiIp: String = "")
