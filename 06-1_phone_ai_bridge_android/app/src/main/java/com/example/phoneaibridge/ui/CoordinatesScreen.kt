package com.example.phoneaibridge.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.phoneaibridge.Graph
import com.example.phoneaibridge.coordinate.CoordinateRagSearcher
import com.example.phoneaibridge.db.entity.MinecraftCoordinateEntity
import kotlinx.coroutines.launch

@Composable
fun CoordinatesScreen() {
    val scope = rememberCoroutineScope()
    val coordinates by Graph.coordinateRepository.observeAll().collectAsState(initial = emptyList())
    var name by remember { mutableStateOf("") }
    var aliases by remember { mutableStateOf("") }
    var world by remember { mutableStateOf("overworld") }
    var x by remember { mutableStateOf("") }
    var y by remember { mutableStateOf("") }
    var z by remember { mutableStateOf("") }
    var tags by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var query by remember { mutableStateOf("") }
    var searchResult by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Coordinates")

        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Add coordinate")
                OutlinedTextField(name, { name = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(aliases, { aliases = it }, label = { Text("Aliases comma separated") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(world, { world = it }, label = { Text("World: overworld/nether/end") }, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    OutlinedTextField(x, { x = it }, label = { Text("X") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f))
                    OutlinedTextField(y, { y = it }, label = { Text("Y") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f))
                    OutlinedTextField(z, { z = it }, label = { Text("Z") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f))
                }
                OutlinedTextField(tags, { tags = it }, label = { Text("Tags comma separated") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(description, { description = it }, label = { Text("Description / memo") }, minLines = 2, modifier = Modifier.fillMaxWidth())
                Button(
                    onClick = {
                        val xValue = x.toDoubleOrNull()
                        val zValue = z.toDoubleOrNull()
                        if (name.isBlank() || xValue == null || zValue == null) {
                            status = "Name, X, Z are required."
                            return@Button
                        }
                        scope.launch {
                            Graph.coordinateRepository.save(
                                MinecraftCoordinateEntity(
                                    name = name.trim(),
                                    aliases = CoordinateRagSearcher.encodeList(CoordinateRagSearcher.splitList(aliases)),
                                    world = CoordinateRagSearcher.normalizeWorld(world),
                                    x = xValue,
                                    y = y.toDoubleOrNull(),
                                    z = zValue,
                                    tags = CoordinateRagSearcher.encodeList(CoordinateRagSearcher.splitList(tags)),
                                    description = description.takeIf { it.isNotBlank() },
                                    createdBy = "app",
                                ),
                            )
                            status = "Saved"
                            name = ""
                            aliases = ""
                            x = ""
                            y = ""
                            z = ""
                            tags = ""
                            description = ""
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Save coordinate")
                }
                if (status.isNotBlank()) Text(status)
            }
        }

        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Search test")
                OutlinedTextField(query, { query = it }, label = { Text("Question") }, modifier = Modifier.fillMaxWidth())
                Button(
                    onClick = {
                        scope.launch {
                            val results = Graph.coordinateRepository.search(query, limit = 8)
                            searchResult = results.joinToString("\n") {
                                "${it.coordinate.name} (${it.coordinate.world}) x=${it.coordinate.x}, y=${it.coordinate.y ?: "-"}, z=${it.coordinate.z} / ${it.reason}"
                            }.ifBlank { "No matching coordinate" }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Search coordinates")
                }
                if (searchResult.isNotBlank()) Text(searchResult)
            }
        }

        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Saved coordinates (${coordinates.size})")
                coordinates.forEach { coordinate ->
                    Column(Modifier.padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("${coordinate.name} / ${coordinate.world}")
                        Text("x=${coordinate.x}, y=${coordinate.y ?: "-"}, z=${coordinate.z}")
                        if (coordinate.aliases.isNotBlank()) Text("aliases: ${coordinate.aliases}")
                        if (coordinate.tags.isNotBlank()) Text("tags: ${coordinate.tags}")
                        coordinate.description?.takeIf { it.isNotBlank() }?.let { Text(it) }
                        OutlinedButton(onClick = { scope.launch { Graph.coordinateRepository.delete(coordinate.id) } }) {
                            Text("Delete")
                        }
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}
