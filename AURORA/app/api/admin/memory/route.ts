import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import { getDataPath, isNotFoundError } from "@/lib/server-files";
import { readdir, readFile } from "fs/promises";
import path from "path";

export const runtime = "nodejs";

function parseJsonlSafe(raw: string) {
  return raw
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(<T>(item: T | null): item is T => item !== null);
}

async function readFileIfExists(filePath: string) {
  try {
    return await readFile(filePath, "utf8");
  } catch (error) {
    if (isNotFoundError(error)) {
      return null;
    }
    throw error;
  }
}

export async function GET(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  const { searchParams } = new URL(request.url);
  const chatId = searchParams.get("chatId");

  if (!chatId) {
    const memoryChatsDir = getDataPath("memory", "chats");

    try {
      const entries = await readdir(memoryChatsDir, { withFileTypes: true });
      const chats = entries
        .filter((entry) => entry.isDirectory())
        .map((entry) => entry.name);
      return NextResponse.json({ chats });
    } catch (error) {
      if (isNotFoundError(error)) {
        return NextResponse.json({ chats: [] });
      }
      throw error;
    }
  }

  const chatDir = getDataPath("memory", "chats", chatId);

  const [stateRaw, documentsRaw, turnsRaw, relationshipRaw] =
    await Promise.all([
      readFileIfExists(path.join(chatDir, "state.json")),
      readFileIfExists(path.join(chatDir, "documents.jsonl")),
      readFileIfExists(path.join(chatDir, "turns.jsonl")),
      readFileIfExists(path.join(chatDir, "relationship.json")),
    ]);

  let state: unknown = null;
  if (stateRaw) {
    try {
      state = JSON.parse(stateRaw);
    } catch {
      // state remains null
    }
  }

  let documents: unknown[] = [];
  if (documentsRaw) {
    const parsed = parseJsonlSafe(documentsRaw);
    documents = parsed.slice(-100);
  }

  let turns: unknown[] = [];
  if (turnsRaw) {
    const parsed = parseJsonlSafe(turnsRaw);
    turns = parsed.slice(-20);
  }

  let relationship: unknown = null;
  if (relationshipRaw) {
    try {
      relationship = JSON.parse(relationshipRaw);
    } catch {
      // relationship remains null
    }
  }

  return NextResponse.json({
    chatId,
    state,
    documents,
    turns,
    relationship,
  });
}
