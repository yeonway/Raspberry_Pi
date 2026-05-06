package com.example.phoneaibridge.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController

private val screens = listOf("Home", "Settings", "Memory", "Knowledge", "Logs")

@Composable
fun AppNavHost() {
    val nav = rememberNavController()
    val backStack by nav.currentBackStackEntryAsState()
    Scaffold(bottomBar = {
        NavigationBar {
            screens.forEach { screen ->
                NavigationBarItem(selected = backStack?.destination?.route == screen, onClick = { nav.navigate(screen) { launchSingleTop = true } }, icon = {}, label = { Text(screen) })
            }
        }
    }) { padding ->
        NavHost(navController = nav, startDestination = "Home", modifier = Modifier.padding(padding).fillMaxSize()) {
            composable("Home") { HomeScreen() }
            composable("Settings") { SettingsScreen() }
            composable("Memory") { MemoryScreen() }
            composable("Knowledge") { KnowledgeScreen() }
            composable("Logs") { LogsScreen() }
        }
    }
}

@Composable
fun Section(title: String, content: @Composable () -> Unit) { Column(Modifier.padding(16.dp)) { Text(title); content() } }
