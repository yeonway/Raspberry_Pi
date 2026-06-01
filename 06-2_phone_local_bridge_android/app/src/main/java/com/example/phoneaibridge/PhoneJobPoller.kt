package com.example.phoneaibridge

import android.content.Context
import android.util.Log
import org.json.JSONObject

object PhoneJobPoller {
    @Volatile private var running = false
    @Volatile private var thread: Thread? = null

    fun start(context: Context) {
        if (thread?.isAlive == true) return
        running = true
        val appContext = context.applicationContext
        thread = Thread({ loop(appContext) }, "phone-ai-job-poller").apply { start() }
    }

    fun stop() {
        running = false
        thread?.interrupt()
        thread = null
    }

    private fun loop(context: Context) {
        while (running) {
            try {
                pollOnce(context)
                Thread.sleep(3000)
            } catch (_: InterruptedException) {
                return
            } catch (e: Exception) {
                BridgeRuntime.recordError(e.message ?: e.javaClass.simpleName)
                Thread.sleep(5000)
            }
        }
    }

    private fun pollOnce(context: Context) {
        val response = DashboardClient.get("/phone/jobs/next")
        val job = response.optJSONObject("job") ?: return
        val jobId = job.optString("id")
        if (jobId.isBlank()) return
        Log.i(TAG, "picked phone AI job $jobId")
        ScreenWake.wakeForJob(context)

        try {
            if (!PhoneLlamaEngine.isLoaded()) {
                PhoneLlamaEngine.loadSelectedModel(context)
            }

            val generated = AnswerGenerator.generate(context, job)
            BridgeRuntime.recordAsk(job.optString("message"), generated.answer)

            DashboardClient.post(
                "/phone/jobs/$jobId/answer",
                JSONObject()
                    .put("answer", generated.answer)
                    .put("usedAi", generated.usedAi)
                    .put("usedRag", generated.usedRag)
                    .put("model", generated.model),
            )
            ScreenWake.wakeForAnswer(context)
            Log.i(TAG, "posted phone AI answer $jobId")
        } catch (e: Exception) {
            val error = e.message ?: e.javaClass.simpleName
            BridgeRuntime.recordError(error)
            runCatching {
                DashboardClient.post(
                    "/phone/jobs/$jobId/fail",
                    JSONObject()
                        .put("error", error)
                        .put("modelLoaded", PhoneLlamaEngine.isLoaded()),
                )
            }.onFailure { postError ->
                BridgeRuntime.recordError(postError.message ?: postError.javaClass.simpleName)
            }
            throw e
        }
    }

    private const val TAG = "PhoneJobPoller"
}
