package com.example.phoneaibridge.paper;

final class AiBridgeException extends RuntimeException {
    AiBridgeException(String message) {
        super(message);
    }

    AiBridgeException(String message, Throwable cause) {
        super(message, cause);
    }
}
