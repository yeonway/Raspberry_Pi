package com.example.phoneaibridge.paper;

import org.bukkit.configuration.file.FileConfiguration;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

final class DashboardEventClient {
    private final HttpClient httpClient;
    private final String baseUrl;
    private final String eventToken;
    private final Duration timeout;

    private DashboardEventClient(String baseUrl, String eventToken, Duration timeout) {
        this.baseUrl = trimTrailingSlash(baseUrl);
        this.eventToken = eventToken == null ? "" : eventToken.trim();
        this.timeout = timeout;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(timeout)
                .build();
    }

    static DashboardEventClient fromConfig(FileConfiguration config) {
        String baseUrl = config.getString("dashboard.base_url", "http://127.0.0.1:8000");
        String token = config.getString("dashboard.event_token", "");
        int timeoutSeconds = Math.max(1, config.getInt("dashboard.timeout_seconds", 10));
        return new DashboardEventClient(baseUrl, token, Duration.ofSeconds(timeoutSeconds));
    }

    String baseUrl() {
        return baseUrl;
    }

    String submit(DashboardEvent event) throws IOException, InterruptedException {
        HttpRequest request = requestBuilder("/event")
                .header("Content-Type", "application/json; charset=utf-8")
                .POST(HttpRequest.BodyPublishers.ofString(event.toJson()))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        requireSuccess(response, "/event");
        return response.body();
    }

    String status() throws IOException, InterruptedException {
        HttpRequest request = requestBuilder("/event/status")
                .GET()
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        requireSuccess(response, "/event/status");
        return response.body();
    }

    private HttpRequest.Builder requestBuilder(String path) {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(timeout)
                .header("Accept", "application/json");

        if (!eventToken.isBlank()) {
            builder.header("X-Event-Token", eventToken);
        }

        return builder;
    }

    private void requireSuccess(HttpResponse<String> response, String path) {
        int status = response.statusCode();
        if (status >= 200 && status < 300) {
            return;
        }

        String body = response.body() == null ? "" : response.body().replaceAll("\\s+", " ").trim();
        if (body.length() > 180) {
            body = body.substring(0, 180) + "...";
        }
        throw new AiBridgeException("Dashboard " + path + " returned HTTP " + status + (body.isBlank() ? "" : ": " + body));
    }

    private static String trimTrailingSlash(String value) {
        String trimmed = value == null ? "" : value.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        if (trimmed.isBlank()) {
            throw new AiBridgeException("dashboard.base_url is empty");
        }
        return trimmed;
    }
}
