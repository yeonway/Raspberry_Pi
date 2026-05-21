package com.example.phoneaibridge.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.example.phoneaibridge.Graph
import com.example.phoneaibridge.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class AiBridgeForegroundService : Service() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val settings = Graph.settings.read()
        val port = settings.port
        startForeground(NOTIFICATION_ID, NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("Phone AI Bridge")
            .setContentText("AI Bridge server running on port $port")
            .setOngoing(true)
            .build())
        Graph.localHttpServer.start()
        if (settings.autoLoadModel) {
            serviceScope.launch {
                val model = Graph.modelStore.current()
                if (model.selected && !model.loaded) {
                    Graph.aiEngine.loadModel(model.localPath)
                }
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        serviceScope.cancel()
        Graph.localHttpServer.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(NotificationChannel(CHANNEL_ID, "Phone AI Bridge", NotificationManager.IMPORTANCE_LOW))
    }

    companion object { private const val CHANNEL_ID = "phone_ai_bridge"; private const val NOTIFICATION_ID = 8765 }
}
