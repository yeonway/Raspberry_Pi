package com.example.phoneaibridge

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager

class BridgeService : Service() {
    private var server: LocalHttpServer? = null
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopBridge()
            stopSelf()
            return START_NOT_STICKY
        }

        startForegroundCompat()
        startBridge()
        return START_STICKY
    }

    override fun onDestroy() {
        stopBridge()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startBridge() {
        if (server != null) return
        acquireWakeLock()
        server = LocalHttpServer(applicationContext).also { it.start() }
        PhoneJobPoller.start(applicationContext)
        Thread({
            if (!PhoneLlamaEngine.isLoaded()) {
                PhoneLlamaEngine.loadSelectedModel(applicationContext)
            }
        }, "phone-ai-autoload").apply {
            isDaemon = true
            start()
        }
    }

    private fun stopBridge() {
        PhoneJobPoller.stop()
        ScreenWake.release()
        server?.stop()
        server = null
        releaseWakeLock()
        if (Build.VERSION.SDK_INT >= 24) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == true) return
        val powerManager = getSystemService(PowerManager::class.java)
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "PhoneAiBridge:ServiceWakeLock",
        ).apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        wakeLock = null
    }

    private fun startForegroundCompat() {
        val notification = buildNotification()
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buildNotification(): Notification {
        val launchIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            launchIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val builder = if (Build.VERSION.SDK_INT >= 26) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }

        return builder
            .setContentTitle(getString(R.string.app_name))
            .setContentText("http://폰IP:${BridgeRuntime.PORT}")
            .setSmallIcon(android.R.drawable.stat_sys_upload_done)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < 26) return
        val manager = getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.app_name),
            NotificationManager.IMPORTANCE_LOW,
        )
        manager.createNotificationChannel(channel)
    }

    companion object {
        const val ACTION_START = "com.example.phoneaibridge.START"
        const val ACTION_STOP = "com.example.phoneaibridge.STOP"
        private const val CHANNEL_ID = "phone_local_bridge"
        private const val NOTIFICATION_ID = 8765
    }
}
