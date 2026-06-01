package com.example.phoneaibridge.paper;

record DashboardCoordinateEvent(
        String playerUuid,
        String playerName,
        String world,
        double x,
        double y,
        double z,
        String description
) {
    String toJson() {
        return "{"
                + "\"type\":\"coordinate_register\","
                + "\"category\":\"coordinate\","
                + "\"player_uuid\":" + Json.quote(playerUuid) + ","
                + "\"player_name\":" + Json.quote(playerName) + ","
                + "\"owner\":" + Json.quote(playerName) + ","
                + "\"name\":" + Json.quote(description) + ","
                + "\"world\":" + Json.quote(world) + ","
                + "\"x\":" + x + ","
                + "\"y\":" + y + ","
                + "\"z\":" + z + ","
                + "\"note\":" + Json.quote(description) + ","
                + "\"message\":" + Json.quote("/\uC88C\uD45C " + format(x) + " " + format(y) + " " + format(z) + ", " + description)
                + "}";
    }

    private static String format(double value) {
        if (Math.rint(value) == value) {
            return Long.toString((long) value);
        }
        return Double.toString(value);
    }
}
