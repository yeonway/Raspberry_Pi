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

class AiBridgeForegroundService : Service() {
    override fun onCreate() {
        super.onCreate()
        createChannel()
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val port = Graph.settings.read().port
        startForeground(NOTIFICATION_ID, NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("Phone AI Bridge")
            .setContentText("AI Bridge server running on port $port")
            .setOngoing(true)
            .build())
        Graph.localHttpServer.start()
        return START_STICKY
    }
    override fun onDestroy() {
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
