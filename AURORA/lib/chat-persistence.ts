import { appendAccountMemory, writeAccountRoom } from "@/lib/account-data";
import { getSessionLogIdentity } from "@/lib/chat-logs";
import type { ModelResult } from "@/lib/chat-provider";
import type { ParsedChatRequest } from "@/lib/chat-request";
import type {
  AuthUser,
  Character,
  ChatTurnAction,
  MemoryItem,
  Message,
  ModelSelection,
  ResponseStyle,
} from "@/types/chat";

export async function persistSuccessfulTurn(
  user: AuthUser | null,
  parsed: ParsedChatRequest,
  assistantContent: string,
): Promise<MemoryItem | undefined> {
  if (!user) {
    return undefined;
  }

  const assistantMessage: Message = {
    id: `assistant-${crypto.randomUUID()}`,
    role: "assistant",
    content: assistantContent,
    createdAt: new Date().toISOString(),
  };

  await writeAccountRoom(user.id, {
    id: parsed.chatId,
    characterId: parsed.character.id,
    customCharacterPrompt: parsed.customCharacterPrompt || undefined,
    title: parsed.chatTitle,
    lastMessage: assistantContent,
    lastMessageAt: formatDateTime(new Date()),
    messages: [...parsed.messages, assistantMessage],
  });

  if (parsed.turnAction !== "message") {
    return undefined;
  }

  const summary = [getLastUserContent(parsed.messages), assistantContent]
    .filter(Boolean)
    .join(" / ")
    .replace(/\s+/g, " ")
    .slice(0, 240);

  return appendAccountMemory(user.id, {
    chatId: parsed.chatId,
    chatTitle: parsed.chatTitle,
    characterId: parsed.character.id,
    characterName: parsed.character.name,
    summary,
    recentCreatedAt: new Date().toISOString(),
  });
}

export function createLogEntry(
  parsed: {
    chatId: string;
    sessionId: string;
    chatTitle: string;
    character: Character;
    messages: Message[];
    modelSelection?: ModelSelection;
    responseStyle: ResponseStyle;
    turnAction: ChatTurnAction;
  },
  result: {
    user?: AuthUser | null;
    assistantContent?: string;
    error?: string;
    modelResult?: ModelResult;
  },
) {
  const sessionIdentity = getSessionLogIdentity({
    userId: result.user?.id,
    userName: result.user?.name,
    sessionId: parsed.sessionId,
  });

  return {
    id: crypto.randomUUID(),
    userId: result.user?.id,
    userName: result.user?.name,
    sessionKey: sessionIdentity.sessionKey,
    sessionName: sessionIdentity.sessionName,
    clientSessionId: parsed.sessionId,
    sessionId: parsed.sessionId,
    chatId: parsed.chatId,
    chatTitle: parsed.chatTitle,
    characterId: parsed.character.id,
    characterName: parsed.character.name,
    responseStyle: parsed.responseStyle,
    requestedModel: result.modelResult?.requestedModel ?? parsed.modelSelection,
    usedModel: result.modelResult?.usedModel,
    fallbackModel: result.modelResult?.fallbackModel,
    usedFallbackModel: result.modelResult?.usedFallbackModel,
    turnAction: parsed.turnAction,
    messages: parsed.messages,
    assistantContent: result.assistantContent,
    error: result.error,
    createdAt: new Date().toISOString(),
  };
}

export function getTurnUserContent(
  messages: Message[],
  turnAction: ChatTurnAction,
) {
  if (turnAction === "skip") {
    return "[Turn skipped by user]";
  }

  return getLastUserContent(messages);
}

function getLastUserContent(messages: Message[]) {
  return (
    messages
      .slice()
      .reverse()
      .find((message) => message.role === "user")?.content ?? ""
  );
}

function formatDateTime(date: Date) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
