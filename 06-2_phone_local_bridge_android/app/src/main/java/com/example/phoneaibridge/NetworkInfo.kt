package com.example.phoneaibridge

import java.net.Inet4Address
import java.net.NetworkInterface
import java.util.Collections

object NetworkInfo {
    fun localIpv4Addresses(): List<String> {
        val result = mutableListOf<String>()
        val interfaces = Collections.list(NetworkInterface.getNetworkInterfaces())
        for (networkInterface in interfaces) {
            if (!networkInterface.isUp || networkInterface.isLoopback) continue
            val addresses = Collections.list(networkInterface.inetAddresses)
            for (address in addresses) {
                if (address is Inet4Address && !address.isLoopbackAddress) {
                    result += address.hostAddress ?: continue
                }
            }
        }
        return result.distinct()
    }
}
