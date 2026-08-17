import type {
  ChatModelsResult,
  SendMessageInput,
  SendMessageResult,
} from "@/types/chat";

type StreamEvent =
  | {
      event: "token";
      content: string;
    }
  | {
      event: "error";
      message: string;
    }
  | {
      event: "done";
      memoryItem?: SendMessageResult["memoryItem"];
    };

export async function sendMessage(
  input: SendMessageInput,
): Promise<SendMessageResult> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      chatId: input.chatId,
      sessionId: input.sessionId,
      chatTitle: input.chatTitle,
      character: input.character,
      customCharacterPrompt: input.customCharacterPrompt,
      messages: input.messages,
      modelSelection: input.modelSelection,
      responseStyle: input.responseStyle,
      turnAction: input.turnAction,
      stream: input.stream ?? true,
    }),
    signal: input.signal,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/event-stream")) {
    return readStreamingMessage(response, input.onToken);
  }

  const payload = (await response.json().catch(() => null)) as
    | Partial<SendMessageResult> & { error?: string }
    | null;

  if (!payload?.content) {
    throw new Error(payload?.error ?? "Chat response was empty.");
  }

  input.onToken?.(payload.content);
  return { content: payload.content, memoryItem: payload.memoryItem };
}

async function readStreamingMessage(
  response: Response,
  onToken: SendMessageInput["onToken"],
): Promise<SendMessageResult> {
  if (!response.body) {
    throw new Error("Streaming response was empty. Please try again.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let content = "";
  let sawDone = false;
  let memoryItem: SendMessageResult["memoryItem"];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() ?? "";

      for (const rawEvent of events) {
        const event = parseSseEvent(rawEvent);
        if (event.event === "token") {
          content += event.content;
          onToken?.(event.content);
        }

        if (event.event === "done") {
          sawDone = true;
          memoryItem = event.memoryItem;
        }

        if (event.event === "error") {
          throw new Error(
            `${event.message} Please retry your message if the answer stopped early.`,
          );
        }
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      const event = parseSseEvent(buffer);
      if (event.event === "token") {
        content += event.content;
        onToken?.(event.content);
      }
      if (event.event === "done") {
        sawDone = true;
        memoryItem = event.memoryItem;
      }
      if (event.event === "error") {
        throw new Error(
          `${event.message} Please retry your message if the answer stopped early.`,
        );
      }
    }
  } catch (error) {
    if (isAbortError(error)) {
      throw new Error("Chat generation was stopped.");
    }

    if (error instanceof Error) {
      throw error;
    }
    throw new Error("The chat stream disconnected. Please retry your message.");
  } finally {
    reader.releaseLock();
  }

  if (!content.trim()) {
    throw new Error("Chat response was empty. Please retry your message.");
  }

  if (!sawDone) {
    throw new Error("The chat stream disconnected. Please retry your message.");
  }

  return { content, memoryItem };
}

function parseSseEvent(rawEvent: string): StreamEvent {
  const lines = rawEvent.split(/\r?\n/);
  const eventName =
    lines.find((line) => line.startsWith("event:"))?.slice(6).trim() ?? "token";
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");

  if (eventName === "done") {
    const payload = parseJsonObject(data);
    return {
      event: "done",
      memoryItem:
        payload && typeof payload.memoryItem === "object"
          ? (payload.memoryItem as SendMessageResult["memoryItem"])
          : undefined,
    };
  }

  try {
    const payload = JSON.parse(data) as { content?: unknown; message?: unknown };
    if (eventName === "error") {
      return {
        event: "error",
        message:
          typeof payload.message === "string"
            ? payload.message
            : "Chat stream failed.",
      };
    }

    return {
      event: "token",
      content: typeof payload.content === "string" ? payload.content : "",
    };
  } catch {
    if (eventName === "error") {
      return { event: "error", message: data || "Chat stream failed." };
    }

    return { event: "token", content: data };
  }
}

function parseJsonObject(data: string) {
  if (!data.trim()) {
    return null;
  }

  try {
    const payload = JSON.parse(data) as unknown;
    return payload && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function isAbortError(error: unknown) {
  return (
    error instanceof DOMException && error.name === "AbortError"
  ) || (error instanceof Error && error.name === "AbortError");
}

async function readErrorMessage(response: Response) {
  const payload = (await response.json().catch(() => null)) as
    | { error?: string }
    | null;

  if (payload?.error) {
    return payload.error;
  }

  const text = await response.text().catch(() => "");
  return text || "Chat response failed. Please retry your message.";
}

export async function fetchAvailableModels(): Promise<ChatModelsResult> {
  const response = await fetch("/api/models", { cache: "no-store" });
  const payload = (await response.json().catch(() => null)) as
    | Partial<ChatModelsResult> & { error?: string }
    | null;

  if (!response.ok || !payload?.defaultModel || !Array.isArray(payload.models)) {
    throw new Error(payload?.error ?? "Model list could not be loaded.");
  }

  return {
    models: payload.models,
    defaultModel: payload.defaultModel,
    providers: Array.isArray(payload.providers) ? payload.providers : [],
    error: payload.error,
    updatedAt: payload.updatedAt ?? new Date().toISOString(),
  };
}
