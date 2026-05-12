package com.example.phoneaibridge.paper;

import org.bukkit.configuration.file.FileConfiguration;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

final class PhoneAiClient {
    private final HttpClient httpClient;
    private final String baseUrl;
    private final String apiToken;
    private final Duration timeout;

    private PhoneAiClient(String baseUrl, String apiToken, Duration timeout) {
        this.baseUrl = trimTrailingSlash(baseUrl);
        this.apiToken = apiToken == null ? "" : apiToken.trim();
        this.timeout = timeout;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(timeout)
                .build();
    }

    static PhoneAiClient fromConfig(FileConfiguration config) {
        String baseUrl = config.getString("phone_ai.base_url", "http://192.168.0.50:8765");
        String token = config.getString("phone_ai.api_token", "");
        int timeoutSeconds = Math.max(1, config.getInt("phone_ai.timeout_seconds", 30));
        return new PhoneAiClient(baseUrl, token, Duration.ofSeconds(timeoutSeconds));
    }

    String baseUrl() {
        return baseUrl;
    }

    AiResponse ask(AiRequest aiRequest) throws IOException, InterruptedException {
        HttpRequest request = requestBuilder("/api/ask")
                .header("Content-Type", "application/json; charset=utf-8")
                .POST(HttpRequest.BodyPublishers.ofString(aiRequest.toJson()))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        requireSuccess(response, "/api/ask");

        String body = response.body();
        String answer = Json.stringValue(body, "answer")
                .filter(value -> !value.isBlank())
                .orElse(body);
        boolean usedMemory = Json.booleanValue(body, "used_memory").orElse(false);
        boolean usedRag = Json.booleanValue(body, "used_rag").orElse(false);
        long latencyMs = Json.longValue(body, "latency_ms").orElse(-1L);
        return new AiResponse(answer, usedMemory, usedRag, latencyMs);
    }

    HealthResponse health() throws IOException, InterruptedException {
        HttpRequest request = requestBuilder("/health")
                .GET()
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        requireSuccess(response, "/health");

        String body = response.body();
        return new HealthResponse(
                Json.booleanValue(body, "ok").orElse(false),
                Json.stringValue(body, "engine").orElse("unknown"),
                Json.booleanValue(body, "model_loaded").orElse(false),
                body
        );
    }

    private HttpRequest.Builder requestBuilder(String path) {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(timeout)
                .header("Accept", "application/json");

        if (!apiToken.isBlank()) {
            builder.header("X-API-Token", apiToken);
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
        throw new AiBridgeException("Phone AI " + path + " returned HTTP " + status + (body.isBlank() ? "" : ": " + body));
    }

    private static String trimTrailingSlash(String value) {
        String trimmed = value == null ? "" : value.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        if (trimmed.isBlank()) {
            throw new AiBridgeException("phone_ai.base_url is empty");
        }
        return trimmed;
    }
}
