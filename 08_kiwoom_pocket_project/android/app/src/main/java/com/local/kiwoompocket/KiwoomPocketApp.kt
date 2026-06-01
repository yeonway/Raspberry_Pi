package com.local.kiwoompocket

import android.app.Application
import com.local.kiwoompocket.di.AppContainer

class KiwoomPocketApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
