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
import kotlinx.coroutines.launch

@Composable
fun KnowledgeScreen() {
    var title by remember { mutableStateOf("철팜 기본 조건") }
    var content by remember { mutableStateOf("철팜은 주민, 침대, 작업대, 골렘 스폰 공간 조건이 중요하다.") }
    var tags by remember { mutableStateOf("iron_farm,villager,golem") }
    var query by remember { mutableStateOf("") }
    var results by remember { mutableStateOf("") }
    val docs by Graph.knowledgeRepository.observeAll().collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Knowledge")
        OutlinedTextField(title, { title = it }, label = { Text("제목") })
        OutlinedTextField(content, { content = it }, label = { Text("내용") })
        OutlinedTextField(tags, { tags = it }, label = { Text("태그") })
        Button(onClick = { scope.launch { Graph.knowledgeRepository.ingest(title, content, "manual", tags) } }) { Text("지식 문서 추가 및 rag_chunks 생성") }
        OutlinedTextField(query, { query = it }, label = { Text("키워드 검색") })
        Button(onClick = { scope.launch { results = Graph.ragSearcher.search(query, 5).joinToString("\n") { "${it.score}: ${it.title} - ${it.chunkText}" } } }) { Text("검색") }
        Text(results)
        LazyColumn { items(docs) { doc -> Column(Modifier.padding(vertical = 6.dp)) { Text(doc.title); Text(doc.tags); Text(doc.content); Button(onClick = { scope.launch { Graph.knowledgeRepository.delete(doc.id) } }) { Text("삭제") }; HorizontalDivider() } } }
    }
}
