import { normalizeResponseStyle } from "@/lib/response-formats";
import type {
  Character,
  ChatTurnAction,
  Message,
  ModelSelection,
  ResponseStyle,
} from "@/types/chat";

type ChatRequestBody = {
  chatId?: unknown;
  sessionId?: unknown;
  chatTitle?: unknown;
  character?: unknown;
  customCharacterPrompt?: unknown;
  messages?: unknown;
  modelSelection?: unknown;
  responseStyle?: unknown;
  turnAction?: unknown;
  stream?: unknown;
};

export type ParsedChatRequest = {
  chatId: string;
  sessionId: string;
  chatTitle: string;
  character: Character;
  customCharacterPrompt: string;
  messages: Message[];
  modelSelection?: ModelSelection;
  responseStyle: ResponseStyle;
  turnAction: ChatTurnAction;
  stream: boolean;
};

export function parseChatRequest(input: unknown): ParsedChatRequest {
  const body = normalizeChatRequestBody(input);

  if (typeof body.chatId !== "string" || !body.chatId.trim()) {
    throw new Error("chatId is required.");
  }

  if (typeof body.sessionId !== "string" || !body.sessionId.trim()) {
    throw new Error("sessionId is required.");
  }

  if (!isCharacter(body.character)) {
    throw new Error("character is invalid.");
  }

  if (!Array.isArray(body.messages) || !body.messages.every(isMessage)) {
    throw new Error("messages are invalid.");
  }

  return {
    chatId: body.chatId,
    sessionId: body.sessionId,
    chatTitle:
      typeof body.chatTitle === "string" && body.chatTitle.trim()
        ? body.chatTitle.trim().slice(0, 120)
        : "New chat",
    character: body.character,
    customCharacterPrompt:
      typeof body.customCharacterPrompt === "string"
        ? body.customCharacterPrompt.trim().slice(0, 4000)
        : "",
    messages: body.messages,
    modelSelection: normalizeModelSelection(body.modelSelection),
    responseStyle: normalizeResponseStyle(body.responseStyle),
    turnAction: body.turnAction === "skip" ? "skip" : "message",
    stream: body.stream !== false,
  };
}

function normalizeChatRequestBody(input: unknown): ChatRequestBody {
  return input && typeof input === "object"
    ? (input as ChatRequestBody)
    : {};
}

function normalizeModelSelection(value: unknown): ModelSelection | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const record = value as Record<string, unknown>;
  if (
    record.provider !== "lmstudio" &&
    record.provider !== "ollama" &&
    record.provider !== "openai" &&
    record.provider !== "deepseek"
  ) {
    return undefined;
  }

  if (typeof record.model !== "string") {
    return undefined;
  }

  const model = record.model.trim().slice(0, 200);
  if (!model) {
    return undefined;
  }

  return {
    provider: record.provider,
    model,
  };
}

function isCharacter(value: unknown): value is Character {
  if (!value || typeof value !== "object") {
    return false;
  }

  const character = value as Record<string, unknown>;
  return (
    typeof character.id === "string" &&
    typeof character.name === "string" &&
    typeof character.avatar === "string" &&
    typeof character.intro === "string" &&
    typeof character.firstScene === "string" &&
    typeof character.personaSummary === "string" &&
    typeof character.modelId === "string" &&
    Array.isArray(character.tags)
  );
}

function isMessage(value: unknown): value is Message {
  if (!value || typeof value !== "object") {
    return false;
  }

  const message = value as Record<string, unknown>;
  return (
    (message.role === "user" || message.role === "assistant") &&
    typeof message.content === "string"
  );
}
