import { mkdir, readFile, appendFile } from "fs/promises";
import path from "path";
import { getDataPath, isNotFoundError, withFileLock } from "@/lib/server-files";
import type { ChatLogEntry, ChatLogSession, Message } from "@/types/chat";

const LOG_FILE_NAME = "chat-logs.jsonl";

function getLogPath() {
  return getDataPath(LOG_FILE_NAME);
}

export async function appendChatLog(entry: ChatLogEntry) {
  const logPath = getLogPath();
  await withFileLock(logPath, async () => {
    await mkdir(path.dirname(logPath), { recursive: true });
    await appendFile(logPath, `${JSON.stringify(entry)}\n`, "utf8");
  });
}

export async function readChatLogs(limit = 200) {
  const logPath = getLogPath();

  try {
    const raw = await readFile(logPath, "utf8");
    return raw
      .split("\n")
      .filter(Boolean)
      .slice(-limit)
      .map(parseChatLogLine)
      .filter((entry): entry is ChatLogEntry => !!entry)
      .reverse();
  } catch (error) {
    if (isNotFoundError(error)) {
      return [];
    }

    throw error;
  }
}

function parseChatLogLine(line: string) {
  try {
    return normalizeChatLogEntry(JSON.parse(line) as ChatLogEntry);
  } catch {
    return null;
  }
}

export function summarizeChatLogSessions(
  logs: ChatLogEntry[],
): ChatLogSession[] {
  const sessions = new Map<string, ChatLogEntry[]>();

  for (const log of logs) {
    const normalizedLog = normalizeChatLogEntry(log);
    const sessionLogs = sessions.get(normalizedLog.sessionKey!) ?? [];
    sessionLogs.push(normalizedLog);
    sessions.set(normalizedLog.sessionKey!, sessionLogs);
  }

  return Array.from(sessions.entries())
    .map(([id, sessionLogs]) => {
      const sortedLogs = sessionLogs
        .slice()
        .sort(
          (left, right) =>
            Date.parse(left.createdAt) - Date.parse(right.createdAt),
        );
      const firstLog = sortedLogs[0];
      const latestLog = sortedLogs[sortedLogs.length - 1];
      const latestUserMessage = getLastMessageByRole(
        latestLog?.messages ?? [],
        "user",
      );

      return {
        id,
        name: latestLog?.sessionName ?? firstLog?.sessionName ?? "Session",
        userId: latestLog?.userId ?? firstLog?.userId,
        sessionIds: uniqueValues(
          sortedLogs.map((log) => log.clientSessionId ?? log.sessionId),
        ),
        chatIds: uniqueValues(sortedLogs.map((log) => log.chatId)),
        chatTitles: uniqueValues(
          sortedLogs.map((log) => log.chatTitle).filter(isPresentString),
        ),
        characterNames: uniqueValues(
          sortedLogs.map((log) => log.characterName).filter(isPresentString),
        ),
        turnCount: sortedLogs.length,
        errorCount: sortedLogs.filter((log) => Boolean(log.error)).length,
        firstAt: firstLog?.createdAt ?? "",
        lastAt: latestLog?.createdAt ?? "",
        latestUserMessage: latestUserMessage?.content,
        latestAssistantContent:
          latestLog?.assistantContent ?? latestLog?.error ?? undefined,
      };
    })
    .sort((left, right) => Date.parse(right.lastAt) - Date.parse(left.lastAt));
}

export function normalizeChatLogEntry(entry: ChatLogEntry): ChatLogEntry {
  const sessionName = getSessionName(entry);
  const sessionKey = getSessionKey(entry, sessionName);

  return {
    ...entry,
    sessionKey,
    sessionName,
    clientSessionId: entry.clientSessionId ?? entry.sessionId,
  };
}

export function getSessionLogIdentity(input: {
  userId?: string;
  userName?: string;
  sessionId: string;
}) {
  const sessionName = cleanLabel(input.userName) ?? "Guest session";
  const sessionKey = input.userId
    ? `user:${input.userId}`
    : `session:${input.sessionId}`;

  return { sessionKey, sessionName };
}

function getSessionName(entry: ChatLogEntry) {
  return (
    cleanLabel(entry.sessionName) ??
    cleanLabel(entry.userName) ??
    getLegacySessionName(entry) ??
    "Guest session"
  );
}

function getSessionKey(entry: ChatLogEntry, sessionName: string) {
  if (entry.sessionKey) {
    return entry.sessionKey;
  }

  if (entry.userId) {
    return `user:${entry.userId}`;
  }

  if (entry.userName) {
    return `name:${slugify(entry.userName)}`;
  }

  if (getLegacySessionName(entry)) {
    return "legacy:combined";
  }

  return `session:${entry.sessionId || slugify(sessionName)}`;
}

function getLegacySessionName(entry: ChatLogEntry) {
  if (
    entry.sessionId.startsWith("codex-") ||
    entry.chatId.startsWith("codex-")
  ) {
    return "Codex verify sessions";
  }

  if (!entry.userId && !entry.userName) {
    return "Legacy sessions";
  }

  return undefined;
}

function cleanLabel(value?: string) {
  const label = value?.trim().replace(/\s+/g, " ");
  return label ? label.slice(0, 80) : undefined;
}

function slugify(value: string) {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "session"
  );
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values.filter(isPresentString)));
}

function isPresentString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function getLastMessageByRole(
  messages: Message[],
  role: Message["role"],
): Message | undefined {
  return messages
    .slice()
    .reverse()
    .find((message) => message.role === role);
}
