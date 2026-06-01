package com.local.kiwoompocket

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.local.kiwoompocket.ui.navigation.AppNavHost
import com.local.kiwoompocket.ui.theme.KiwoomPocketTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val appContainer = (application as KiwoomPocketApp).container
        setContent {
            KiwoomPocketTheme {
                AppNavHost(container = appContainer)
            }
        }
    }
}
