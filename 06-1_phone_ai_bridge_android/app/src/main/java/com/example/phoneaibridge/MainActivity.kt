package com.example.phoneaibridge

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.core.content.ContextCompat
import com.example.phoneaibridge.service.AiBridgeForegroundService
import com.example.phoneaibridge.ui.AppNavHost

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1001)
        if (Graph.settings.read().autoStartServer) {
            ContextCompat.startForegroundService(this, Intent(this, AiBridgeForegroundService::class.java))
        }
        setContent {
            MaterialTheme(colorScheme = lightColorScheme()) { AppNavHost() }
        }
    }
}
