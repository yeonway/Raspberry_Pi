package com.example.phoneaibridge.paper;

record AiResponse(String answer, boolean usedMemory, boolean usedRag, long latencyMs) {
}
