package com.example.phoneaibridge

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.os.PowerManager

object ScreenWake {
    private const val JOB_WAKE_MS = 5 * 60 * 1000L
    private const val ANSWER_WAKE_MS = 30 * 1000L

    @Volatile private var wakeLock: PowerManager.WakeLock? = null

    fun wakeForJob(context: Context) {
        acquire(context, "AiJob", JOB_WAKE_MS)
        openApp(context)
    }

    fun wakeForAnswer(context: Context) {
        acquire(context, "AiAnswer", ANSWER_WAKE_MS)
        openApp(context)
    }

    fun release() {
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        wakeLock = null
    }

    @SuppressLint("WakelockTimeout")
    @Suppress("DEPRECATION")
    private fun acquire(context: Context, reason: String, timeoutMs: Long) {
        val powerManager = context.applicationContext.getSystemService(PowerManager::class.java)
        val flags = PowerManager.SCREEN_BRIGHT_WAKE_LOCK or
            PowerManager.ACQUIRE_CAUSES_WAKEUP or
            PowerManager.ON_AFTER_RELEASE

        release()
        wakeLock = powerManager.newWakeLock(flags, "PhoneAiBridge:$reason").apply {
            setReferenceCounted(false)
            acquire(timeoutMs)
        }
    }

    private fun openApp(context: Context) {
        val appContext = context.applicationContext
        val intent = Intent(appContext, MainActivity::class.java).apply {
            addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP or
                    Intent.FLAG_ACTIVITY_REORDER_TO_FRONT,
            )
        }
        runCatching { appContext.startActivity(intent) }
    }
}
