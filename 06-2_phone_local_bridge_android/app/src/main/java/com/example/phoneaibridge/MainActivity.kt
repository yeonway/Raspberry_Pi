package com.example.phoneaibridge

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.app.KeyguardManager
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())

    private lateinit var bridgeStatusText: TextView
    private lateinit var bridgeAddressText: TextView
    private lateinit var bridgeRequestText: TextView
    private lateinit var bridgeQuestionText: TextView
    private lateinit var bridgeAnswerText: TextView
    private lateinit var modelStatusText: TextView
    private lateinit var modelNameText: TextView
    private lateinit var dashboardAddressText: TextView
    private lateinit var minecraftAddressText: TextView
    private lateinit var minecraftStatusText: TextView
    private lateinit var aiStatusText: TextView
    private lateinit var aiQueueText: TextView
    private lateinit var aiCurrentJobText: TextView
    private lateinit var ragStatusText: TextView
    private lateinit var commandResultText: TextView

    private val refreshTask = object : Runnable {
        override fun run() {
            refreshBridge()
            handler.postDelayed(this, 1000)
        }
    }

    private val dashboardRefreshTask = object : Runnable {
        override fun run() {
            refreshDashboardStatus(showProgress = false)
            handler.postDelayed(this, 3000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        configureScreenWakeBehavior()
        requestNotificationPermission()
        requestBatteryOptimizationExemption()
        buildUi()
        startBridge()
        refreshDashboardStatus()
    }

    override fun onResume() {
        super.onResume()
        configureScreenWakeBehavior()
        handler.post(refreshTask)
        handler.post(dashboardRefreshTask)
    }

    override fun onPause() {
        handler.removeCallbacks(refreshTask)
        handler.removeCallbacks(dashboardRefreshTask)
        super.onPause()
    }

    @Deprecated("Deprecated in Android API, sufficient for this simple debug app")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQUEST_MODEL || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        val flags = data.flags and (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
        runCatching { contentResolver.takePersistableUriPermission(uri, flags) }
        runPhoneTask("모델 복사 중") {
            val copied = PhoneLlamaEngine.copyModelFromUri(this, uri)
            if (copied) {
                runOnUiThread { commandResultText.text = "모델 복사 완료. 모델 로드를 누르세요." }
            } else {
                runOnUiThread { commandResultText.text = PhoneLlamaEngine.snapshot(this).optString("lastError") }
            }
            refreshBridgeOnUi()
        }
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(18), dp(20), dp(18))
            setBackgroundColor(Color.rgb(248, 250, 252))
        }

        root.addView(title("Phone Local Bridge"))
        root.addView(subtitle("Minecraft 로컬 제어 + 폰 AI"))

        val bridgePanel = panel(root)
        bridgePanel.addView(sectionTitle("폰 브리지"))
        bridgePanel.addView(buttonRow(
            actionButton("켜기", Color.rgb(37, 99, 235)) { startBridge() },
            actionButton("끄기", Color.rgb(71, 85, 105)) { stopBridge() },
            actionButton("복사", Color.rgb(22, 101, 52)) { copyText(BridgeRuntime.snapshot(this).optString("url")) },
        ))
        bridgeStatusText = row(bridgePanel, "상태")
        bridgeAddressText = row(bridgePanel, "주소")
        bridgeRequestText = row(bridgePanel, "요청")
        bridgeQuestionText = row(bridgePanel, "최근 질문")
        bridgeAnswerText = row(bridgePanel, "최근 답변")

        val modelPanel = panel(root)
        modelPanel.addView(sectionTitle("폰 AI 모델"))
        modelPanel.addView(buttonRow(
            actionButton("모델 선택", Color.rgb(37, 99, 235)) { chooseModel() },
            actionButton("모델 로드", Color.rgb(22, 101, 52)) { loadModel() },
            actionButton("언로드", Color.rgb(71, 85, 105)) { unloadModel() },
        ))
        modelStatusText = row(modelPanel, "모델 상태")
        modelNameText = row(modelPanel, "모델 파일")

        val dashboardPanel = panel(root)
        dashboardPanel.addView(sectionTitle("라즈베리파이"))
        dashboardPanel.addView(buttonRow(
            actionButton("상태", Color.rgb(37, 99, 235)) { refreshDashboardStatus() },
            actionButton("대시보드", Color.rgb(22, 101, 52)) { copyText(DashboardClient.DASHBOARD_URL) },
            actionButton("서버주소", Color.rgb(22, 101, 52)) { copyText(DashboardClient.MINECRAFT_ADDRESS) },
        ))
        dashboardAddressText = row(dashboardPanel, "대시보드")
        minecraftAddressText = row(dashboardPanel, "마크 서버")
        minecraftStatusText = row(dashboardPanel, "마크 상태")
        aiStatusText = row(dashboardPanel, "AI 연결")
        aiQueueText = row(dashboardPanel, "AI 대기열")
        aiCurrentJobText = row(dashboardPanel, "현재 AI 작업")

        val controlPanel = panel(root)
        controlPanel.addView(sectionTitle("Minecraft 제어"))
        controlPanel.addView(buttonRow(
            actionButton("시작", Color.rgb(37, 99, 235)) { minecraftCommand("start") },
            actionButton("중지", Color.rgb(185, 28, 28)) { minecraftCommand("stop") },
            actionButton("재시작", Color.rgb(147, 51, 234)) { minecraftCommand("restart") },
        ))
        controlPanel.addView(buttonRow(
            actionButton("AI 테스트", Color.rgb(15, 118, 110)) { askTest() },
            actionButton("좌표동기화", Color.rgb(79, 70, 229)) { syncCoordinates() },
            actionButton("새로고침", Color.rgb(71, 85, 105)) { refreshDashboardStatus() },
        ))
        commandResultText = row(controlPanel, "결과")

        val ragPanel = panel(root)
        ragPanel.addView(sectionTitle("RAG 지식 / 좌표"))
        ragPanel.addView(buttonRow(
            actionButton("지식 추가", Color.rgb(37, 99, 235)) { showKnowledgeDialog() },
            actionButton("지식 보기", Color.rgb(22, 101, 52)) { showKnowledgeList() },
            actionButton("좌표 보기", Color.rgb(79, 70, 229)) { showCoordinateList() },
        ))
        ragStatusText = row(ragPanel, "저장 상태")

        val scroll = ScrollView(this)
        scroll.addView(root)
        setContentView(scroll)
    }

    private fun chooseModel() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
        }
        startActivityForResult(intent, REQUEST_MODEL)
    }

    private fun loadModel() {
        runPhoneTask("모델 로드 중") {
            val ok = PhoneLlamaEngine.loadSelectedModel(this)
            runOnUiThread {
                commandResultText.text = if (ok) "모델 로드 완료" else PhoneLlamaEngine.snapshot(this).optString("lastError")
            }
            refreshBridgeOnUi()
        }
    }

    private fun unloadModel() {
        PhoneLlamaEngine.unload()
        commandResultText.text = "모델 언로드 완료"
        refreshBridge()
    }

    private fun title(textValue: String): TextView {
        return TextView(this).apply {
            text = textValue
            textSize = 25f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(15, 23, 42))
        }
    }

    private fun subtitle(textValue: String): TextView {
        return TextView(this).apply {
            text = textValue
            textSize = 14f
            setTextColor(Color.rgb(71, 85, 105))
            setPadding(0, dp(4), 0, dp(14))
        }
    }

    private fun sectionTitle(textValue: String): TextView {
        return TextView(this).apply {
            text = textValue
            textSize = 18f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(15, 23, 42))
            setPadding(0, 0, 0, dp(10))
        }
    }

    private fun panel(root: LinearLayout): LinearLayout {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = rounded(Color.WHITE)
        }
        root.addView(panel, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        ).apply { topMargin = dp(12) })
        return panel
    }

    private fun buttonRow(vararg buttons: Button): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(4), 0, dp(6))
            buttons.forEachIndexed { index, button ->
                addView(button)
                if (index != buttons.lastIndex) addView(space(dp(8), 1))
            }
        }
    }

    private fun row(parent: LinearLayout, label: String): TextView {
        parent.addView(TextView(this).apply {
            text = label
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(71, 85, 105))
            setPadding(0, dp(8), 0, dp(2))
        })

        val valueView = TextView(this).apply {
            text = "-"
            textSize = 15f
            setTextColor(Color.rgb(15, 23, 42))
            setTextIsSelectable(true)
        }
        parent.addView(valueView)
        return valueView
    }

    private fun actionButton(label: String, color: Int, onClick: () -> Unit): Button {
        return Button(this).apply {
            text = label
            textSize = 12f
            setTextColor(Color.WHITE)
            minHeight = dp(42)
            minWidth = 0
            minimumWidth = 0
            background = rounded(color)
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(0, dp(42), 1f)
        }
    }

    private fun refreshBridgeOnUi() {
        runOnUiThread { refreshBridge() }
    }

    private fun refreshBridge() {
        val snapshot = BridgeRuntime.snapshot(this)
        val ai = snapshot.optJSONObject("ai") ?: JSONObject()
        bridgeStatusText.text = if (snapshot.optBoolean("running")) "실행 중" else "꺼짐"
        bridgeAddressText.text = snapshot.optString("url")
        bridgeRequestText.text = "${snapshot.optLong("requestCount")} (${snapshot.optString("lastPath")})"
        bridgeQuestionText.text = snapshot.optString("lastQuestion").ifBlank { "-" }
        bridgeAnswerText.text = snapshot.optString("lastAnswer").ifBlank { "-" }
        if (::ragStatusText.isInitialized) {
            ragStatusText.text = "지식 ${KnowledgeStore.count(this)}개 / 좌표 ${CoordinateStore.count(this)}개"
        }
        modelStatusText.text = when {
            ai.optBoolean("loaded") -> "로드됨"
            ai.optBoolean("loading") -> "작업 중"
            ai.optBoolean("selected") -> "선택됨"
            else -> "모델 없음"
        } + " / " + ai.optString("lastMessage")
        modelNameText.text = ai.optString("modelName").ifBlank { "-" }
        dashboardAddressText.text = DashboardClient.DASHBOARD_URL
        minecraftAddressText.text = DashboardClient.MINECRAFT_ADDRESS
    }

    private fun refreshDashboardStatus(showProgress: Boolean = true) {
        runDashboardTask(if (showProgress) "상태 확인 중" else "") {
            val data = DashboardClient.get("/status")
            val services = data.optJSONObject("services") ?: JSONObject()
            val ai = data.optJSONObject("ai") ?: JSONObject()
            val phoneHealth = ai.optJSONObject("phone_ai_health")
            runOnUiThread {
                minecraftStatusText.text = serviceLabel(services.optString("minecraft_server"))
                aiStatusText.text = formatAiConnection(ai, phoneHealth)
                aiQueueText.text = formatAiQueue(ai)
                aiCurrentJobText.text = formatAiCurrentJob(ai)
                if (showProgress) {
                    commandResultText.text = "상태 확인 완료"
                }
            }
        }
    }

    private fun formatAiConnection(ai: JSONObject, phoneHealth: JSONObject?): String {
        return when {
            ai.optBoolean("phone_pull_mode") -> "폰 pull 연결"
            phoneHealth?.optBoolean("modelLoaded") == true -> "폰 AI 로드됨"
            else -> "모델 로드 필요"
        }
    }

    private fun formatAiQueue(ai: JSONObject): String {
        val dashboardQueue = ai.optInt("queue_size")
        val phoneQueue = ai.optInt("phone_job_queue_size")
        val inFlight = ai.optInt("phone_job_in_flight")
        val processed = ai.optInt("processed")
        val failed = ai.optInt("failed")
        return "대시보드 $dashboardQueue / 폰대기 $phoneQueue / 처리중 $inFlight / 완료 $processed / 실패 $failed"
    }

    private fun formatAiCurrentJob(ai: JSONObject): String {
        val current = ai.optJSONObject("current_job")
        if (current != null) {
            val player = current.optString("player_name", "-").ifBlank { "-" }
            val question = current.optString("question", "-").ifBlank { "-" }
            val startedAt = current.optString("started_at", "").ifBlank { "" }
            return if (startedAt.isBlank()) {
                "$player: $question"
            } else {
                "$player: $question ($startedAt)"
            }
        }

        val last = ai.optJSONObject("last_answer") ?: return "없음"
        val player = last.optString("player_name", "-").ifBlank { "-" }
        val answer = last.optString("answer", "").ifBlank { "-" }
        val time = last.optString("time", "").ifBlank { "" }
        return if (time.isBlank()) {
            "최근 답변 $player: $answer"
        } else {
            "최근 답변 $player: $answer ($time)"
        }
    }

    private fun minecraftCommand(action: String) {
        runDashboardTask("Minecraft $action 실행 중") {
            val data = DashboardClient.post("/minecraft/$action")
            val services = data.optJSONObject("services") ?: JSONObject()
            val message = data.optString("message", "완료")
            runOnUiThread {
                minecraftStatusText.text = serviceLabel(services.optString("minecraft_server"))
                commandResultText.text = message
            }
        }
    }

    private fun askTest() {
        runPhoneTask("AI 테스트 중") {
            if (!PhoneLlamaEngine.isLoaded()) {
                PhoneLlamaEngine.loadSelectedModel(this)
            }
            val payload = JSONObject()
                .put("player_name", "PhoneApp")
                .put("message", "다이아 어디서 캐는 게 좋아?")
                .put("max_tokens", 50)
            val data = AnswerGenerator.generate(this, payload)
            runOnUiThread {
                aiStatusText.text = if (data.usedAi) "폰 AI 응답" else "모델 로드 필요"
                commandResultText.text = data.answer
                refreshBridge()
            }
        }
    }

    private fun syncCoordinates() {
        runDashboardTask("좌표 동기화 중") {
            val data = DashboardClient.post("/coordinate-sync")
            runOnUiThread {
                commandResultText.text = data.optString("message", "좌표 동기화 완료")
                refreshDashboardStatus()
            }
        }
    }

    private fun showKnowledgeDialog() {
        val input = EditText(this).apply {
            hint = "첫 줄: 제목\n둘째 줄부터: 내용\n마지막 줄 선택: #태그 #마크"
            minLines = 6
            gravity = Gravity.TOP
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        }

        AlertDialog.Builder(this)
            .setTitle("RAG 지식 추가")
            .setView(input)
            .setPositiveButton("저장") { _, _ ->
                val lines = input.text.toString().lines().map { it.trim() }.filter { it.isNotBlank() }
                if (lines.isEmpty()) {
                    commandResultText.text = "지식 제목과 내용을 입력하세요."
                    return@setPositiveButton
                }

                val title = lines.first()
                val bodyLines = lines.drop(1)
                val tags = bodyLines
                    .lastOrNull()
                    ?.split(Regex("\\s+"))
                    ?.filter { it.startsWith("#") }
                    ?.map { it.removePrefix("#") }
                    .orEmpty()
                val content = bodyLines
                    .filterNot { line -> line.split(Regex("\\s+")).all { it.startsWith("#") } }
                    .joinToString("\n")
                    .ifBlank { title }

                runCatching {
                    KnowledgeStore.upsert(
                        this,
                        JSONObject()
                            .put("title", title)
                            .put("content", content)
                            .put("tags", org.json.JSONArray(tags)),
                    )
                }.onSuccess {
                    commandResultText.text = "지식 저장 완료: ${it.title}"
                    refreshBridge()
                }.onFailure {
                    commandResultText.text = it.message ?: "지식 저장 실패"
                }
            }
            .setNegativeButton("취소", null)
            .show()
    }

    private fun showKnowledgeList() {
        val items = KnowledgeStore.list(this)
        commandResultText.text = if (items.isEmpty()) {
            "저장된 지식 없음"
        } else {
            items.take(8).joinToString("\n") { "- ${it.title}: ${it.content.take(60)}" }
        }
        refreshBridge()
    }

    private fun showCoordinateList() {
        val items = CoordinateStore.list(this)
        commandResultText.text = if (items.isEmpty()) {
            "저장된 좌표 없음"
        } else {
            items.take(8).joinToString("\n") { "- ${it.name} ${it.world} x=${it.x.toInt()} z=${it.z.toInt()}" }
        }
        refreshBridge()
    }

    private fun runDashboardTask(progress: String, task: () -> Unit) {
        if (progress.isNotBlank()) {
            commandResultText.text = progress
        }
        Thread {
            try {
                task()
            } catch (e: Exception) {
                runOnUiThread {
                    if (progress.isNotBlank()) {
                        commandResultText.text = e.message ?: "실패"
                    }
                    aiStatusText.text = "확인 필요"
                }
            }
        }.start()
    }

    private fun runPhoneTask(progress: String, task: () -> Unit) {
        commandResultText.text = progress
        Thread {
            try {
                task()
            } catch (e: Exception) {
                runOnUiThread { commandResultText.text = e.message ?: "실패" }
            }
        }.start()
    }

    private fun serviceLabel(value: String): String {
        return when (value) {
            "running" -> "실행 중"
            "stopped" -> "중지됨"
            "start_requested" -> "시작 요청됨"
            "stop_requested" -> "중지 요청됨"
            "restart_requested" -> "재시작 요청됨"
            else -> value.ifBlank { "-" }
        }
    }

    private fun startBridge() {
        val intent = Intent(this, BridgeService::class.java).setAction(BridgeService.ACTION_START)
        if (Build.VERSION.SDK_INT >= 26) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        refreshBridge()
    }

    private fun stopBridge() {
        startService(Intent(this, BridgeService::class.java).setAction(BridgeService.ACTION_STOP))
        refreshBridge()
    }

    private fun copyText(value: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Phone Local Bridge", value))
        Toast.makeText(this, "복사됨: $value", Toast.LENGTH_SHORT).show()
    }

    private fun rounded(color: Int): GradientDrawable {
        return GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(8).toFloat()
        }
    }

    private fun space(width: Int, height: Int): View {
        return View(this).apply {
            layoutParams = LinearLayout.LayoutParams(width, height)
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT < 33) return
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 33)
    }

    private fun requestBatteryOptimizationExemption() {
        if (Build.VERSION.SDK_INT < 23) return
        val powerManager = getSystemService(PowerManager::class.java)
        if (powerManager.isIgnoringBatteryOptimizations(packageName)) return
        val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
            data = Uri.parse("package:$packageName")
        }
        runCatching { startActivity(intent) }
    }

    private fun configureScreenWakeBehavior() {
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
            runCatching {
                getSystemService(KeyguardManager::class.java)
                    .requestDismissKeyguard(this, null)
            }
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                    WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD,
            )
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    companion object {
        private const val REQUEST_MODEL = 1001
    }
}
