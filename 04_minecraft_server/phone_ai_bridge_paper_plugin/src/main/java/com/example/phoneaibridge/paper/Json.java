package com.example.phoneaibridge.paper;

import java.util.Optional;

final class Json {
    private Json() {
    }

    static String quote(String value) {
        if (value == null) {
            return "null";
        }

        StringBuilder out = new StringBuilder(value.length() + 16);
        out.append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\b' -> out.append("\\b");
                case '\f' -> out.append("\\f");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        out.append('"');
        return out.toString();
    }

    static Optional<String> stringValue(String json, String key) {
        int valueStart = valueStart(json, key);
        if (valueStart < 0 || json.charAt(valueStart) != '"') {
            return Optional.empty();
        }

        StringBuilder out = new StringBuilder();
        for (int i = valueStart + 1; i < json.length(); i++) {
            char c = json.charAt(i);
            if (c == '"') {
                return Optional.of(out.toString());
            }
            if (c == '\\' && i + 1 < json.length()) {
                char escaped = json.charAt(++i);
                switch (escaped) {
                    case '"' -> out.append('"');
                    case '\\' -> out.append('\\');
                    case '/' -> out.append('/');
                    case 'b' -> out.append('\b');
                    case 'f' -> out.append('\f');
                    case 'n' -> out.append('\n');
                    case 'r' -> out.append('\r');
                    case 't' -> out.append('\t');
                    case 'u' -> {
                        if (i + 4 < json.length()) {
                            String hex = json.substring(i + 1, i + 5);
                            try {
                                out.append((char) Integer.parseInt(hex, 16));
                                i += 4;
                            } catch (NumberFormatException ignored) {
                                out.append("\\u").append(hex);
                                i += 4;
                            }
                        }
                    }
                    default -> out.append(escaped);
                }
            } else {
                out.append(c);
            }
        }
        return Optional.empty();
    }

    static Optional<Boolean> booleanValue(String json, String key) {
        int valueStart = valueStart(json, key);
        if (valueStart < 0) {
            return Optional.empty();
        }
        if (json.startsWith("true", valueStart)) {
            return Optional.of(true);
        }
        if (json.startsWith("false", valueStart)) {
            return Optional.of(false);
        }
        return Optional.empty();
    }

    static Optional<Long> longValue(String json, String key) {
        int valueStart = valueStart(json, key);
        if (valueStart < 0) {
            return Optional.empty();
        }

        int end = valueStart;
        while (end < json.length()) {
            char c = json.charAt(end);
            if (!Character.isDigit(c) && c != '-') {
                break;
            }
            end++;
        }

        if (end == valueStart) {
            return Optional.empty();
        }

        try {
            return Optional.of(Long.parseLong(json.substring(valueStart, end)));
        } catch (NumberFormatException e) {
            return Optional.empty();
        }
    }

    private static int valueStart(String json, String key) {
        if (json == null || key == null) {
            return -1;
        }

        String quotedKey = "\"" + key + "\"";
        int keyIndex = json.indexOf(quotedKey);
        if (keyIndex < 0) {
            return -1;
        }

        int colon = json.indexOf(':', keyIndex + quotedKey.length());
        if (colon < 0) {
            return -1;
        }

        int valueStart = colon + 1;
        while (valueStart < json.length() && Character.isWhitespace(json.charAt(valueStart))) {
            valueStart++;
        }
        return valueStart < json.length() ? valueStart : -1;
    }
}
