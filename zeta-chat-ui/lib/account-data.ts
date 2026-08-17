import { mkdir, readFile, rm, writeFile } from "fs/promises";
import { randomUUID } from "crypto";
import path from "path";
import {
  DEFAULT_RESPONSE_STYLE,
  normalizeResponseStyle,
} from "@/lib/response-formats";
import {
  getDataPath,
  isNotFoundError,
  readJsonFile,
  sanitizePathSegment,
  withFileLock,
  writeJsonFile,
} from "@/lib/server-files";
import type {
  AccountChatState,
  ChatRoom,
  MemoryItem,
  ResponseStyle,
} from "@/types/chat";

const ACCOUNT_DIR_NAME = "accounts";
const ROOMS_FILE_NAME = "rooms.json";
const MEMORIES_FILE_NAME = "memories.jsonl";
const RESPONSE_STYLE_FILE_NAME = "response-style.json";
const MAX_MEMORY_ITEMS = 500;

function getAccountDir(userId: string) {
  return getDataPath(ACCOUNT_DIR_NAME, sanitizePathSegment(userId));
}

function getRoomsPath(userId: string) {
  return path.join(getAccountDir(userId), ROOMS_FILE_NAME);
}

function getMemoriesPath(userId: string) {
  return path.join(getAccountDir(userId), MEMORIES_FILE_NAME);
}

function getResponseStylePath(userId: string) {
  return path.join(getAccountDir(userId), RESPONSE_STYLE_FILE_NAME);
}

export function normalizeAccountRoom(value: unknown): ChatRoom | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const room = value as Partial<ChatRoom>;
  if (
    typeof room.id !== "string" ||
    typeof room.characterId !== "string" ||
    typeof room.title !== "string" ||
    typeof room.lastMessage !== "string" ||
    typeof room.lastMessageAt !== "string" ||
    !Array.isArray(room.messages)
  ) {
    return null;
  }

  return {
    id: room.id,
    characterId: room.characterId,
    title: room.title,
    lastMessage: room.lastMessage,
    lastMessageAt: room.lastMessageAt,
    archivedAt:
      typeof room.archivedAt === "string" ? room.archivedAt : undefined,
    customCharacterPrompt:
      typeof room.customCharacterPrompt === "string"
        ? room.customCharacterPrompt
        : undefined,
    messages: room.messages.filter(
      (message) =>
        message &&
        typeof message === "object" &&
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string" &&
        typeof message.createdAt === "string",
    ) as ChatRoom["messages"],
  };
}

function normalizeMemoryItem(value: unknown): MemoryItem | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const item = value as Partial<MemoryItem>;
  if (
    typeof item.id !== "string" ||
    typeof item.chatId !== "string" ||
    typeof item.chatTitle !== "string" ||
    typeof item.characterId !== "string" ||
    typeof item.characterName !== "string" ||
    typeof item.summary !== "string" ||
    typeof item.recentCreatedAt !== "string" ||
    typeof item.createdAt !== "string"
  ) {
    return null;
  }

  return {
    id: item.id,
    chatId: item.chatId,
    chatTitle: item.chatTitle,
    characterId: item.characterId,
    characterName: item.characterName,
    summary: item.summary,
    recentCreatedAt: item.recentCreatedAt,
    createdAt: item.createdAt,
  };
}

export async function readAccountRooms(userId: string) {
  const rawRooms = await readJsonFile<unknown[]>(getRoomsPath(userId), [], {
    recoverTrailingData: true,
  });
  return rawRooms
    .map(normalizeAccountRoom)
    .filter((room): room is ChatRoom => !!room);
}

export async function writeAccountRoom(userId: string, room: ChatRoom) {
  const normalizedRoom = normalizeAccountRoom(room);
  if (!normalizedRoom) {
    throw new Error("room is invalid.");
  }

  const filePath = getRoomsPath(userId);
  await withFileLock(filePath, async () => {
    const rooms = await readAccountRooms(userId);
    const nextRooms = [
      normalizedRoom,
      ...rooms.filter((currentRoom) => currentRoom.id !== normalizedRoom.id),
    ];
    await writeJsonFile(filePath, nextRooms);
  });
}

export async function deleteAccountRoom(userId: string, roomId: string) {
  const filePath = getRoomsPath(userId);
  await withFileLock(filePath, async () => {
    const rooms = await readAccountRooms(userId);
    const nextRooms = rooms.filter((room) => room.id !== roomId);

    if (nextRooms.length === rooms.length) {
      return;
    }

    if (nextRooms.length === 0) {
      await rm(filePath, { force: true });
      return;
    }

    await writeJsonFile(filePath, nextRooms);
  });
}

export async function readAccountMemories(userId: string, limit = 100) {
  try {
    const raw = await readFile(getMemoriesPath(userId), "utf8");
    return raw
      .split("\n")
      .filter(Boolean)
      .map(parseMemoryLine)
      .filter((item): item is MemoryItem => !!item)
      .slice(-Math.min(limit, MAX_MEMORY_ITEMS))
      .reverse();
  } catch (error) {
    if (isNotFoundError(error)) {
      return [];
    }

    throw error;
  }
}

export async function appendAccountMemory(
  userId: string,
  item: Omit<MemoryItem, "id" | "createdAt">,
) {
  const memoryItem: MemoryItem = {
    ...item,
    id: randomUUID(),
    createdAt: new Date().toISOString(),
  };
  const filePath = getMemoriesPath(userId);
  await withFileLock(filePath, async () => {
    await mkdir(path.dirname(filePath), { recursive: true });
    await writeFile(filePath, `${JSON.stringify(memoryItem)}\n`, {
      encoding: "utf8",
      flag: "a",
    });
  });
  return memoryItem;
}

export async function readAccountResponseStyle(
  userId: string,
): Promise<ResponseStyle> {
  const rawStyle = await readJsonFile<unknown | null>(
    getResponseStylePath(userId),
    null,
    { recoverTrailingData: true },
  );

  if (!rawStyle) {
    return DEFAULT_RESPONSE_STYLE;
  }

  return normalizeResponseStyle(rawStyle);
}

export async function writeAccountResponseStyle(
  userId: string,
  responseStyle: ResponseStyle,
) {
  const normalizedStyle = normalizeResponseStyle(responseStyle);
  const filePath = getResponseStylePath(userId);
  await withFileLock(filePath, async () => {
    await writeJsonFile(filePath, normalizedStyle);
  });
  return normalizedStyle;
}

export async function readAccountState(
  userId: string,
): Promise<AccountChatState> {
  const [rooms, memories, responseStyle] = await Promise.all([
    readAccountRooms(userId),
    readAccountMemories(userId),
    readAccountResponseStyle(userId),
  ]);

  return { rooms, memories, responseStyle };
}

function parseMemoryLine(line: string) {
  try {
    return normalizeMemoryItem(JSON.parse(line));
  } catch {
    return null;
  }
}
