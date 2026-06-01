package com.example.presettimer

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.text.InputFilter
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.max

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private val timerStore by lazy { TimerStore(this) }

    private lateinit var timerText: TextView
    private lateinit var statusText: TextView
    private lateinit var listContainer: LinearLayout
    private lateinit var startPauseButton: Button
    private lateinit var resetButton: Button
    private lateinit var selectedNameText: TextView

    private var timers = mutableListOf<TimerPreset>()
    private var selectedId: Long = 0L
    private var running = false
    private var remainingMillis = 0L
    private var endAtMillis = 0L

    private val tick = object : Runnable {
        override fun run() {
            if (!running) return

            remainingMillis = max(0L, endAtMillis - SystemClock.elapsedRealtime())
            renderTimer()

            if (remainingMillis == 0L) {
                running = false
                startPauseButton.text = "Start"
                statusText.text = "Finished"
                notifyFinished()
                return
            }

            handler.postDelayed(this, 200L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        timers = timerStore.load().toMutableList()
        selectedId = timers.firstOrNull()?.id ?: 0L
        remainingMillis = selectedTimer()?.durationMillis ?: DEFAULT_DURATION_MILLIS

        buildUi()
        renderAll()
    }

    override fun onPause() {
        handler.removeCallbacks(tick)
        super.onPause()
    }

    override fun onResume() {
        super.onResume()
        if (running) handler.post(tick)
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(16), dp(18), dp(18))
            setBackgroundColor(SURFACE)
        }

        root.addView(title("Preset Timer"))
        root.addView(subtitle("Save named timers and run them like clock presets."))

        val activePanel = panel(root)
        selectedNameText = TextView(this).apply {
            textSize = 16f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(TEXT)
            gravity = Gravity.CENTER
        }
        timerText = TextView(this).apply {
            textSize = 52f
            typeface = Typeface.MONOSPACE
            setTextColor(TEXT)
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, dp(14), 0, dp(8))
        }
        statusText = TextView(this).apply {
            textSize = 14f
            setTextColor(MUTED)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(14))
        }
        activePanel.addView(selectedNameText)
        activePanel.addView(timerText)
        activePanel.addView(statusText)
        activePanel.addView(buttonRow(
            actionButton("Start", BLUE) { toggleTimer() }.also { startPauseButton = it },
            actionButton("Reset", SLATE) { resetTimer() }.also { resetButton = it },
        ))

        val presetsPanel = panel(root)
        presetsPanel.addView(sectionHeader("Saved Timers", "Add") { showEditDialog(null) })
        listContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        presetsPanel.addView(listContainer)

        val scroll = ScrollView(this)
        scroll.addView(root)
        setContentView(scroll)
    }

    private fun renderAll() {
        if (timers.isEmpty()) {
            timers.add(TimerPreset(nextId(), "Tea break", DEFAULT_DURATION_MILLIS))
            timerStore.save(timers)
            selectedId = timers.first().id
        }

        if (selectedTimer() == null) {
            selectedId = timers.first().id
            remainingMillis = timers.first().durationMillis
        }

        renderTimer()
        renderList()
    }

    private fun renderTimer() {
        val selected = selectedTimer()
        selectedNameText.text = selected?.name ?: "No timer"
        timerText.text = formatMillis(remainingMillis)
        statusText.text = when {
            running -> "Running"
            remainingMillis == 0L -> "Ready to reset"
            else -> "Ready"
        }
        startPauseButton.text = if (running) "Pause" else "Start"
        resetButton.isEnabled = selected != null
    }

    private fun renderList() {
        listContainer.removeAllViews()

        timers.forEach { preset ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(12), dp(10), dp(12), dp(10))
                background = rounded(if (preset.id == selectedId) SELECTED else Color.WHITE, dp(8))
            }

            val top = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            top.addView(TextView(this).apply {
                text = preset.name
                textSize = 16f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(TEXT)
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            top.addView(TextView(this).apply {
                text = formatMillis(preset.durationMillis)
                textSize = 18f
                typeface = Typeface.MONOSPACE
                setTextColor(BLUE)
            })
            row.addView(top)

            row.addView(buttonRow(
                smallButton("Use", BLUE) { selectTimer(preset.id) },
                smallButton("Edit", SLATE) { showEditDialog(preset) },
                smallButton("Delete", RED) { confirmDelete(preset) },
            ))

            listContainer.addView(row, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            ).apply { topMargin = dp(10) })
        }
    }

    private fun selectTimer(id: Long) {
        selectedId = id
        running = false
        handler.removeCallbacks(tick)
        remainingMillis = selectedTimer()?.durationMillis ?: 0L
        renderAll()
    }

    private fun toggleTimer() {
        val selected = selectedTimer() ?: return
        if (remainingMillis <= 0L) remainingMillis = selected.durationMillis

        running = !running
        if (running) {
            endAtMillis = SystemClock.elapsedRealtime() + remainingMillis
            handler.post(tick)
        } else {
            handler.removeCallbacks(tick)
        }
        renderTimer()
    }

    private fun resetTimer() {
        running = false
        handler.removeCallbacks(tick)
        remainingMillis = selectedTimer()?.durationMillis ?: 0L
        renderTimer()
    }

    private fun showEditDialog(existing: TimerPreset?) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(2), dp(6), dp(2), 0)
        }

        val nameInput = dialogInput("Name", existing?.name.orEmpty(), InputType.TYPE_CLASS_TEXT)
        val minutesInput = dialogInput(
            "Minutes",
            ((existing?.durationMillis ?: DEFAULT_DURATION_MILLIS) / 60000L).toString(),
            InputType.TYPE_CLASS_NUMBER,
        )
        val secondsInput = dialogInput(
            "Seconds",
            (((existing?.durationMillis ?: DEFAULT_DURATION_MILLIS) / 1000L) % 60L).toString(),
            InputType.TYPE_CLASS_NUMBER,
        )

        content.addView(nameInput)
        content.addView(minutesInput)
        content.addView(secondsInput)

        AlertDialog.Builder(this)
            .setTitle(if (existing == null) "Add timer" else "Edit timer")
            .setView(content)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save", null)
            .create()
            .apply {
                setOnShowListener {
                    getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                        val name = nameInput.text.toString().trim()
                        val minutes = minutesInput.text.toString().toLongOrNull() ?: 0L
                        val seconds = secondsInput.text.toString().toLongOrNull() ?: 0L
                        val durationMillis = ((minutes * 60L) + seconds.coerceIn(0L, 59L)) * 1000L

                        when {
                            name.isBlank() -> toast("Enter a timer name.")
                            durationMillis <= 0L -> toast("Enter a duration greater than zero.")
                            else -> {
                                saveTimer(existing, name, durationMillis)
                                dismiss()
                            }
                        }
                    }
                }
            }
            .show()
    }

    private fun saveTimer(existing: TimerPreset?, name: String, durationMillis: Long) {
        if (existing == null) {
            val preset = TimerPreset(nextId(), name, durationMillis)
            timers.add(preset)
            selectedId = preset.id
            remainingMillis = durationMillis
        } else {
            val index = timers.indexOfFirst { it.id == existing.id }
            if (index >= 0) {
                timers[index] = existing.copy(name = name, durationMillis = durationMillis)
                if (existing.id == selectedId) {
                    running = false
                    handler.removeCallbacks(tick)
                    remainingMillis = durationMillis
                }
            }
        }
        timerStore.save(timers)
        renderAll()
    }

    private fun confirmDelete(preset: TimerPreset) {
        if (timers.size == 1) {
            toast("Keep at least one timer.")
            return
        }

        AlertDialog.Builder(this)
            .setTitle("Delete timer")
            .setMessage("Delete ${preset.name}?")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Delete") { _, _ ->
                timers.removeAll { it.id == preset.id }
                if (selectedId == preset.id) {
                    selectedId = timers.first().id
                    remainingMillis = timers.first().durationMillis
                    running = false
                    handler.removeCallbacks(tick)
                }
                timerStore.save(timers)
                renderAll()
            }
            .show()
    }

    private fun selectedTimer(): TimerPreset? = timers.firstOrNull { it.id == selectedId }

    private fun nextId(): Long = (timers.maxOfOrNull { it.id } ?: 0L) + 1L

    private fun notifyFinished() {
        ToneGenerator(AudioManager.STREAM_ALARM, 90).startTone(ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD, 900)
        val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(600L, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(600L)
        }
    }

    private fun title(value: String): TextView = TextView(this).apply {
        text = value
        textSize = 27f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(TEXT)
    }

    private fun subtitle(value: String): TextView = TextView(this).apply {
        text = value
        textSize = 14f
        setTextColor(MUTED)
        setPadding(0, dp(4), 0, dp(12))
    }

    private fun sectionHeader(label: String, actionLabel: String, action: () -> Unit): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(TextView(this@MainActivity).apply {
                text = label
                textSize = 18f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(TEXT)
            }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(smallButton(actionLabel, GREEN, action))
        }
    }

    private fun panel(root: LinearLayout): LinearLayout {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(14), dp(14), dp(14))
            background = rounded(Color.WHITE, dp(8))
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
            setPadding(0, dp(8), 0, 0)
            buttons.forEachIndexed { index, button ->
                addView(button)
                if (index != buttons.lastIndex) addView(space(dp(8), 1))
            }
        }
    }

    private fun actionButton(label: String, color: Int, onClick: () -> Unit): Button {
        return Button(this).apply {
            text = label
            textSize = 14f
            setTextColor(Color.WHITE)
            minWidth = 0
            minimumWidth = 0
            minHeight = dp(46)
            background = rounded(color, dp(8))
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(0, dp(46), 1f)
        }
    }

    private fun smallButton(label: String, color: Int, onClick: () -> Unit): Button {
        return Button(this).apply {
            text = label
            textSize = 12f
            setTextColor(Color.WHITE)
            minWidth = 0
            minimumWidth = 0
            minHeight = dp(38)
            background = rounded(color, dp(8))
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(0, dp(38), 1f)
        }
    }

    private fun dialogInput(hintValue: String, value: String, type: Int): EditText {
        return EditText(this).apply {
            hint = hintValue
            setText(value)
            inputType = type
            filters = arrayOf(InputFilter.LengthFilter(40))
            setSingleLine(true)
            setPadding(dp(10), dp(6), dp(10), dp(6))
        }
    }

    private fun rounded(color: Int, radius: Int): GradientDrawable {
        return GradientDrawable().apply {
            setColor(color)
            cornerRadius = radius.toFloat()
        }
    }

    private fun space(width: Int, height: Int): View {
        return View(this).apply {
            layoutParams = LinearLayout.LayoutParams(width, height)
        }
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun formatMillis(value: Long): String {
        val totalSeconds = value / 1000L
        val minutes = totalSeconds / 60L
        val seconds = totalSeconds % 60L
        return "%02d:%02d".format(minutes, seconds)
    }

    data class TimerPreset(
        val id: Long,
        val name: String,
        val durationMillis: Long,
    )

    class TimerStore(context: Context) {
        private val prefs = context.getSharedPreferences("timers", MODE_PRIVATE)

        fun load(): List<TimerPreset> {
            val raw = prefs.getString(KEY_TIMERS, null) ?: return defaultTimers()
            return runCatching {
                val array = JSONArray(raw)
                (0 until array.length()).mapNotNull { index ->
                    val item = array.optJSONObject(index) ?: return@mapNotNull null
                    TimerPreset(
                        id = item.optLong("id"),
                        name = item.optString("name"),
                        durationMillis = item.optLong("durationMillis"),
                    ).takeIf { it.id > 0 && it.name.isNotBlank() && it.durationMillis > 0L }
                }.ifEmpty { defaultTimers() }
            }.getOrElse { defaultTimers() }
        }

        fun save(timers: List<TimerPreset>) {
            val array = JSONArray()
            timers.forEach { timer ->
                array.put(JSONObject()
                    .put("id", timer.id)
                    .put("name", timer.name)
                    .put("durationMillis", timer.durationMillis))
            }
            prefs.edit().putString(KEY_TIMERS, array.toString()).apply()
        }

        private fun defaultTimers(): List<TimerPreset> {
            return listOf(
                TimerPreset(1L, "3 minute timer", 3L * 60L * 1000L),
                TimerPreset(2L, "5 minute timer", 5L * 60L * 1000L),
            )
        }

        companion object {
            private const val KEY_TIMERS = "saved_timers"
        }
    }

    companion object {
        private const val DEFAULT_DURATION_MILLIS = 3L * 60L * 1000L

        private val SURFACE = Color.rgb(246, 247, 249)
        private val TEXT = Color.rgb(17, 24, 39)
        private val MUTED = Color.rgb(91, 100, 115)
        private val BLUE = Color.rgb(37, 99, 235)
        private val GREEN = Color.rgb(22, 101, 52)
        private val SLATE = Color.rgb(75, 85, 99)
        private val RED = Color.rgb(185, 28, 28)
        private val SELECTED = Color.rgb(236, 244, 255)
    }
}
