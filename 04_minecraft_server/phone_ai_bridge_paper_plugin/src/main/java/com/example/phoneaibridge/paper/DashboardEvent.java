package com.example.phoneaibridge.paper;

record DashboardEvent(
        String playerUuid,
        String playerName,
        String message,
        String serverContext,
        String coordinateContext,
        int maxTokens
) {
    String toJson() {
        return "{"
                + "\"type\":\"chat_ai\","
                + "\"category\":\"qa\","
                + "\"player_uuid\":" + Json.quote(playerUuid) + ","
                + "\"player_name\":" + Json.quote(playerName) + ","
                + "\"message\":" + Json.quote(message) + ","
                + "\"server_context\":" + Json.quote(serverContext) + ","
                + "\"coordinate_context\":" + Json.quote(coordinateContext) + ","
                + "\"spark_context\":\"\","
                + "\"max_tokens\":" + maxTokens
                + "}";
    }
}
