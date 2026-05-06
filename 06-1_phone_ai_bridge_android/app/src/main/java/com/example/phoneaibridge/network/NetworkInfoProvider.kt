package com.example.phoneaibridge.network

import java.net.Inet4Address
import java.net.NetworkInterface
import java.util.Collections

data class NetworkInfo(
    val primaryIp: String?,
    val localIps: List<String>,
    val apiBaseUrl: String?,
    val healthUrl: String?,
)

object NetworkInfoProvider {
    fun getNetworkInfo(port: Int): NetworkInfo {
        val ips = getLocalIpv4Addresses()
        val primary = ips.firstOrNull()
        val apiBaseUrl = primary?.let { "http://$it:$port" }
        return NetworkInfo(
            primaryIp = primary,
            localIps = ips,
            apiBaseUrl = apiBaseUrl,
            healthUrl = apiBaseUrl?.let { "$it/health" },
        )
    }

    fun getLocalIpv4Addresses(): List<String> {
        return runCatching {
            Collections.list(NetworkInterface.getNetworkInterfaces())
                .flatMap { networkInterface ->
                    Collections.list(networkInterface.inetAddresses)
                        .filterIsInstance<Inet4Address>()
                        .filterNot { it.isLoopbackAddress }
                        .filterNot { it.isLinkLocalAddress }
                        .map { address -> NetworkAddress(networkInterface.name.orEmpty(), address.hostAddress.orEmpty()) }
                }
                .filter { it.ip.isNotBlank() }
                .sortedWith(
                    compareBy<NetworkAddress> { if (it.interfaceName == "wlan0") 0 else 1 }
                        .thenBy { it.interfaceName }
                        .thenBy { it.ip },
                )
                .map { it.ip }
                .distinct()
        }.getOrDefault(emptyList())
    }

    private data class NetworkAddress(val interfaceName: String, val ip: String)
}
