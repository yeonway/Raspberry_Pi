package com.example.minecraftadmin

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())

    private lateinit var urlInput: EditText
    private lateinit var tokenInput: EditText
    private lateinit var minecraftAddressInput: EditText
    private lateinit var dashboardText: TextView
    private lateinit var minecraftText: TextView
    private lateinit var systemText: TextView
    private lateinit var aiQueueText: TextView
    private lateinit var currentAiText: TextView
    private lateinit var commandInput: EditText
    private lateinit var resultText: TextView

    private val refreshTask = object : Runnable {
        override fun run() {
            refreshStatus(showProgress = false)
            handler.postDelayed(this, 5000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        handler.post(refreshTask)
    }

    override fun onPause() {
        handler.removeCallbacks(refreshTask)
        super.onPause()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(16), dp(18), dp(18))
            setBackgroundColor(Color.rgb(248, 250, 252))
        }

        root.addView(title("Minecraft Admin"))
        root.addView(subtitle("외부 접속용 라즈베리파이 / 마크 서버 관리자"))

        val connectPanel = panel(root)
        connectPanel.addView(sectionTitle("연결"))
        urlInput = input("대시보드 URL", DashboardClient.dashboardUrl(this), singleLine = true)
        tokenInput = input("이벤트 토큰", DashboardClient.eventToken(this), singleLine = true)
        minecraftAddressInput = input("마크 서버 주소", DashboardClient.minecraftAddress(this), singleLine = true)
        connectPanel.addView(urlInput)
        connectPanel.addView(tokenInput)
        connectPanel.addView(minecraftAddressInput)
        connectPanel.addView(buttonRow(
            actionButton("저장", BLUE) { saveSettings() },
            actionButton("새로고침", SLATE) { refreshStatus() },
        ))
        connectPanel.addView(buttonRow(
            actionButton("대시보드 열기", GREEN) { openDashboard() },
            actionButton("주소 복사", GREEN) { copyText(DashboardClient.minecraftAddress(this)) },
        ))

        val statusPanel = panel(root)
        statusPanel.addView(sectionTitle("상태"))
        dashboardText = row(statusPanel, "대시보드")
        minecraftText = row(statusPanel, "마크 서버")
        systemText = row(statusPanel, "시스템")
        aiQueueText = row(statusPanel, "AI 대기열")
        currentAiText = row(statusPanel, "현재 AI")

        val controlPanel = panel(root)
        controlPanel.addView(sectionTitle("서버 제어"))
        controlPanel.addView(buttonRow(
            actionButton("시작", BLUE) { minecraftAction("start") },
            actionButton("중지", RED) { minecraftAction("stop") },
            actionButton("재시작", PURPLE) { minecraftAction("restart") },
        ))
        controlPanel.addView(buttonRow(
            actionButton("상태", SLATE) { minecraftAction("status", method = "GET") },
            actionButton("백업", TEAL) { runBackup() },
            actionButton("좌표동기화", INDIGO) { syncCoordinates() },
        ))

        val commandPanel = panel(root)
        commandPanel.addView(sectionTitle("마크 명령어"))
        commandInput = input("예: list, say 공지, time set day", "", singleLine = true)
        commandPanel.addView(commandInput)
        commandPanel.addView(buttonRow(
            actionButton("실행", RED) { sendRconCommand() },
            actionButton("목록", SLATE) { quickCommand("list") },
            actionButton("저장", SLATE) { quickCommand("save-all") },
        ))
        commandPanel.addView(buttonRow(
            actionButton("낮", BLUE) { quickCommand("time set day") },
            actionButton("맑음", BLUE) { quickCommand("weather clear") },
            actionButton("TPS", TEAL) { quickCommand("tps") },
        ))

        val dataPanel = panel(root)
        dataPanel.addView(sectionTitle("조회"))
        dataPanel.addView(buttonRow(
            actionButton("로그", SLATE) { loadLogs() },
            actionButton("좌표", INDIGO) { loadCoordinates() },
            actionButton("AI상태", TEAL) { loadAiStatus() },
        ))
        resultText = row(dataPanel, "결과")

        val scroll = ScrollView(this)
        scroll.addView(root)
        setContentView(scroll)
    }

    private fun saveSettings() {
        DashboardClient.save(
            this,
            urlInput.text.toString(),
            tokenInput.text.toString(),
            minecraftAddressInput.text.toString(),
        )
        Toast.makeText(this, "저장 완료", Toast.LENGTH_SHORT).show()
        refreshStatus()
    }

    private fun refreshStatus(showProgress: Boolean = true) {
        runTask(if (showProgress) "상태 확인 중..." else "") {
            val data = DashboardClient.get(this, "/status")
            val system = data.optJSONObject("system") ?: JSONObject()
            val services = data.optJSONObject("services") ?: JSONObject()
            val ai = data.optJSONObject("ai") ?: JSONObject()
            runOnUiThread {
                dashboardText.text = DashboardClient.dashboardUrl(this)
                minecraftText.text = "${DashboardClient.minecraftAddress(this)} / ${serviceLabel(services.optString("minecraft_server"))}"
                systemText.text = formatSystem(system)
                aiQueueText.text = formatAiQueue(ai)
                currentAiText.text = formatCurrentAi(ai)
                if (showProgress) resultText.text = "상태 확인 완료"
            }
        }
    }

    private fun minecraftAction(action: String, method: String = "POST") {
        runTask("Minecraft $action 실행 중...") {
            val data = if (method == "GET") {
                DashboardClient.get(this, "/minecraft/$action")
            } else {
                DashboardClient.post(this, "/minecraft/$action")
            }
            runOnUiThread {
                resultText.text = data.optString("message", data.toString(2))
                refreshStatus(showProgress = false)
            }
        }
    }

    private fun runBackup() {
        runTask("백업 실행 중...") {
            val data = DashboardClient.post(this, "/backup/run")
            runOnUiThread { resultText.text = data.optString("message", data.toString(2)) }
        }
    }

    private fun syncCoordinates() {
        runTask("좌표 동기화 중...") {
            val data = DashboardClient.post(this, "/coordinate-sync")
            runOnUiThread { resultText.text = data.optString("message", data.toString(2)) }
        }
    }

    private fun sendRconCommand() {
        val command = commandInput.text.toString().trim().removePrefix("/")
        if (command.isBlank()) {
            resultText.text = "명령어를 입력하세요."
            return
        }
        runTask("명령 실행 중: $command") {
            val data = DashboardClient.post(this, "/command", JSONObject().put("command", command))
            val text = data.optString("output").ifBlank {
                data.optString("message", data.toString(2))
            }
            runOnUiThread { resultText.text = text.ifBlank { "명령 실행 완료" } }
        }
    }

    private fun quickCommand(command: String) {
        commandInput.setText(command)
        sendRconCommand()
    }

    private fun loadLogs() {
        runTask("로그 불러오는 중...") {
            val data = DashboardClient.get(this, "/logs?lines=120")
            val logs = data.optJSONArray("logs")
            val text = if (logs == null || logs.length() == 0) {
                "로그 없음"
            } else {
                (0 until logs.length()).joinToString("") { logs.optString(it) }
            }
            runOnUiThread { resultText.text = text.trim().takeLast(5000) }
        }
    }

    private fun loadCoordinates() {
        runTask("좌표 불러오는 중...") {
            val data = DashboardClient.post(
                this,
                "/coordinate-list",
                JSONObject().put("owner", "admin-app").put("all", true),
            )
            runOnUiThread { resultText.text = data.optString("text", data.toString(2)) }
        }
    }

    private fun loadAiStatus() {
        runTask("AI 상태 확인 중...") {
            val data = DashboardClient.get(this, "/event/status")
            runOnUiThread {
                resultText.text = data.toString(2)
                aiQueueText.text = formatAiQueue(data)
                currentAiText.text = formatCurrentAi(data)
            }
        }
    }

    private fun formatSystem(system: JSONObject): String {
        val cpu = system.optDouble("cpu_percent", -1.0)
        val ram = system.optDouble("ram_percent", -1.0)
        val temp = system.opt("temperature_c")
        val disk = system.opt("disk_percent")
        return "CPU ${percent(cpu)} / RAM ${percent(ram)} / 온도 ${temp ?: "-"}C / 디스크 ${disk ?: "-"}%"
    }

    private fun formatAiQueue(ai: JSONObject): String {
        return "대시보드 ${ai.optInt("queue_size")} / 폰대기 ${ai.optInt("phone_job_queue_size")} / 처리중 ${ai.optInt("phone_job_in_flight")} / 완료 ${ai.optInt("processed")} / 실패 ${ai.optInt("failed")}"
    }

    private fun formatCurrentAi(ai: JSONObject): String {
        val current = ai.optJSONObject("current_job")
        if (current != null) {
            return "${current.optString("player_name", "-")}: ${current.optString("question", "-")} (${current.optString("started_at", "-")})"
        }
        val last = ai.optJSONObject("last_answer") ?: return "없음"
        return "최근 ${last.optString("player_name", "-")}: ${last.optString("answer", "-")} (${last.optString("time", "-")})"
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

    private fun percent(value: Double): String {
        return if (value < 0) "-" else "%.1f%%".format(value)
    }

    private fun runTask(progress: String, task: () -> Unit) {
        if (progress.isNotBlank() && ::resultText.isInitialized) {
            resultText.text = progress
        }
        Thread {
            try {
                task()
            } catch (e: Exception) {
                runOnUiThread { resultText.text = e.message ?: "실패" }
            }
        }.start()
    }

    private fun openDashboard() {
        runCatching {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(DashboardClient.dashboardUrl(this))))
        }.onFailure {
            resultText.text = it.message ?: "브라우저 열기 실패"
        }
    }

    private fun copyText(value: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Minecraft Admin", value))
        Toast.makeText(this, "복사됨: $value", Toast.LENGTH_SHORT).show()
    }

    private fun title(textValue: String): TextView {
        return TextView(this).apply {
            text = textValue
            textSize = 26f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(15, 23, 42))
        }
    }

    private fun subtitle(textValue: String): TextView {
        return TextView(this).apply {
            text = textValue
            textSize = 14f
            setTextColor(Color.rgb(71, 85, 105))
            setPadding(0, dp(4), 0, dp(12))
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
            setPadding(dp(14), dp(12), dp(14), dp(14))
            background = rounded(Color.WHITE)
        }
        root.addView(
            panel,
            LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                .apply { topMargin = dp(12) },
        )
        return panel
    }

    private fun input(hintValue: String, value: String, singleLine: Boolean): EditText {
        return EditText(this).apply {
            hint = hintValue
            setText(value)
            textSize = 14f
            setSingleLine(singleLine)
            inputType = if (singleLine) {
                InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            } else {
                InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            }
            setPadding(dp(10), dp(8), dp(10), dp(8))
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
        val value = TextView(this).apply {
            text = "-"
            textSize = 15f
            setTextColor(Color.rgb(15, 23, 42))
            setTextIsSelectable(true)
        }
        parent.addView(value)
        return value
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

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    companion object {
        private val BLUE = Color.rgb(37, 99, 235)
        private val GREEN = Color.rgb(22, 101, 52)
        private val SLATE = Color.rgb(71, 85, 105)
        private val RED = Color.rgb(185, 28, 28)
        private val PURPLE = Color.rgb(147, 51, 234)
        private val TEAL = Color.rgb(15, 118, 110)
        private val INDIGO = Color.rgb(79, 70, 229)
    }
}
