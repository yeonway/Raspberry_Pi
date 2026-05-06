package com.example.phoneaibridge.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.phoneaibridge.Graph
import com.example.phoneaibridge.db.entity.PlayerMemoryEntity
import kotlinx.coroutines.launch

@Composable
fun MemoryScreen() {
    var query by remember { mutableStateOf("") }
    var uuid by remember { mutableStateOf("test-uuid") }
    var name by remember { mutableStateOf("Steve") }
    var summary by remember { mutableStateOf("Steve는 철팜을 만들고 있으며 주민 운반 중이다.") }
    var goal by remember { mutableStateOf("철팜 제작") }
    val list by Graph.playerMemoryRepository.search(query).collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Memory")
        OutlinedTextField(query, { query = it }, label = { Text("player_uuid / player_name 검색") })
        OutlinedTextField(uuid, { uuid = it }, label = { Text("player_uuid") })
        OutlinedTextField(name, { name = it }, label = { Text("player_name") })
        OutlinedTextField(summary, { summary = it }, label = { Text("summary") })
        OutlinedTextField(goal, { goal = it }, label = { Text("current_goal") })
        Button(onClick = { scope.launch { Graph.playerMemoryRepository.save(PlayerMemoryEntity(playerUuid = uuid, playerName = name, summary = summary, currentGoal = goal, confidence = 0.8)) } }) { Text("테스트 메모리 추가/수정") }
        LazyColumn { items(list) { item -> Column(Modifier.padding(vertical = 6.dp)) { Text("${item.playerName} (${item.playerUuid})"); Text("목표: ${item.currentGoal ?: "-"}"); Text(item.summary); Text("마지막 업데이트: ${item.updatedAt}"); HorizontalDivider() } } }
    }
}
