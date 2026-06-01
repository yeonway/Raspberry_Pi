package com.local.kiwoompocket.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.automirrored.filled.ReceiptLong
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.local.kiwoompocket.di.AppContainer
import com.local.kiwoompocket.ui.account.AccountScreen
import com.local.kiwoompocket.ui.account.AccountViewModel
import com.local.kiwoompocket.ui.components.AppTopBar
import com.local.kiwoompocket.ui.conditions.ConditionsScreen
import com.local.kiwoompocket.ui.conditions.ConditionsViewModel
import com.local.kiwoompocket.ui.home.HomeScreen
import com.local.kiwoompocket.ui.home.HomeViewModel
import com.local.kiwoompocket.ui.orders.MockOrderScreen
import com.local.kiwoompocket.ui.orders.MockOrderViewModel
import com.local.kiwoompocket.ui.settings.SettingsScreen
import com.local.kiwoompocket.ui.settings.SettingsViewModel
import com.local.kiwoompocket.ui.stockdetail.StockDetailScreen
import com.local.kiwoompocket.ui.stockdetail.StockDetailViewModel
import com.local.kiwoompocket.ui.watchlist.WatchlistScreen
import com.local.kiwoompocket.ui.watchlist.WatchlistViewModel

private data class NavItem(
    val route: String,
    val title: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
)

private val bottomItems = listOf(
    NavItem("home", "홈", Icons.Default.Home),
    NavItem("account", "계좌", Icons.Default.AccountBalance),
    NavItem("watchlist", "관심", Icons.AutoMirrored.Filled.List),
    NavItem("conditions", "조건", Icons.Default.Search),
    NavItem("orders", "모의", Icons.AutoMirrored.Filled.ReceiptLong),
    NavItem("settings", "설정", Icons.Default.Settings),
)

@Composable
fun AppNavHost(container: AppContainer) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route ?: "home"
    val title = bottomItems.firstOrNull { currentRoute.startsWith(it.route) }?.title ?: "종목 상세"

    Scaffold(
        topBar = { AppTopBar(title = title) },
        bottomBar = {
            NavigationBar {
                bottomItems.forEach { item ->
                    NavigationBarItem(
                        selected = currentRoute.startsWith(item.route),
                        onClick = {
                            navController.navigate(item.route) {
                                launchSingleTop = true
                                restoreState = true
                                popUpTo(navController.graph.startDestinationId) {
                                    saveState = true
                                }
                            }
                        },
                        icon = { Icon(item.icon, contentDescription = item.title) },
                        label = { Text(item.title) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            route = "root",
            modifier = Modifier.padding(padding),
        ) {
            composable("home") {
                val vm: HomeViewModel = viewModel(
                    factory = viewModelFactory {
                        HomeViewModel(container.accountRepository, container.watchlistRepository, container.settingsRepository)
                    }
                )
                val state by vm.state.collectAsStateWithLifecycle()
                HomeScreen(
                    state = state,
                    onRefresh = vm::refresh,
                    onSettings = { navController.navigate("settings") },
                )
            }
            composable("account") {
                val vm: AccountViewModel = viewModel(factory = viewModelFactory { AccountViewModel(container.accountRepository) })
                val state by vm.state.collectAsStateWithLifecycle()
                AccountScreen(state = state, onRefresh = vm::refresh)
            }
            composable("watchlist") {
                val vm: WatchlistViewModel = viewModel(
                    factory = viewModelFactory {
                        WatchlistViewModel(container.watchlistRepository, container.stockRepository, container.webSocketManager)
                    }
                )
                val state by vm.state.collectAsStateWithLifecycle()
                WatchlistScreen(
                    state = state,
                    onAdd = vm::add,
                    onDelete = vm::delete,
                    onRefresh = vm::refresh,
                    onRefreshQuote = vm::refreshQuote,
                    onOpenDetail = { code -> navController.navigate("stock/$code") },
                    onRealtimeConnect = vm::connectRealtime,
                    onRealtimeDisconnect = vm::disconnectRealtime,
                )
            }
            composable(
                route = "stock/{code}",
                arguments = listOf(navArgument("code") { type = NavType.StringType }),
            ) { entry ->
                val vm: StockDetailViewModel = viewModel(factory = viewModelFactory { StockDetailViewModel(container.stockRepository) })
                val code = entry.arguments?.getString("code").orEmpty()
                LaunchedEffect(code) { vm.setCode(code) }
                val state by vm.state.collectAsStateWithLifecycle()
                StockDetailScreen(state = state, onRefresh = vm::refresh)
            }
            composable("conditions") {
                val vm: ConditionsViewModel = viewModel(factory = viewModelFactory { ConditionsViewModel(container.conditionRepository) })
                val state by vm.state.collectAsStateWithLifecycle()
                ConditionsScreen(state = state, onRefresh = vm::refresh, onRun = vm::run)
            }
            composable("orders") {
                val vm: MockOrderViewModel = viewModel(
                    factory = viewModelFactory { MockOrderViewModel(container.settingsRepository, container.orderRepository) }
                )
                val state by vm.state.collectAsStateWithLifecycle()
                MockOrderScreen(
                    state = state,
                    onCodeChange = vm::updateCode,
                    onQtyChange = vm::updateQty,
                    onPriceChange = vm::updatePrice,
                    onBuy = { vm.submit("buy") },
                    onSell = { vm.submit("sell") },
                )
            }
            composable("settings") {
                val vm: SettingsViewModel = viewModel(
                    factory = viewModelFactory { SettingsViewModel(container.settingsRepository, container.accountRepository) }
                )
                val state by vm.state.collectAsStateWithLifecycle()
                SettingsScreen(
                    state = state,
                    onServerChange = vm::updateServerBaseUrl,
                    onTokenChange = vm::updateBridgeApiToken,
                    onMockModeChange = vm::updateMockMode,
                    onRefreshIntervalChange = vm::updateRefreshInterval,
                    onSave = vm::save,
                    onTest = vm::testConnection,
                )
            }
        }
    }
}

private fun <T : ViewModel> viewModelFactory(create: () -> T): ViewModelProvider.Factory {
    return object : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <VM : ViewModel> create(modelClass: Class<VM>): VM = create() as VM
    }
}
