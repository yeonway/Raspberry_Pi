import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import { readBotConfig } from "@/lib/bot-config";
import {
  readCollections,
  readLorebooks,
  readPlaces,
  readWorlds,
} from "@/lib/admin-store";
import { readChatLogs, summarizeChatLogSessions } from "@/lib/chat-logs";

export const runtime = "nodejs";

type SearchResult = {
  type: string;
  id: string;
  label: string;
  description: string;
  link: string;
};

function matchesQuery(text: string, query: string) {
  return text.toLowerCase().includes(query);
}

export async function GET(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim();
  if (!q) {
    return NextResponse.json({ results: [], total: 0 });
  }

  const query = q.toLowerCase();
  const results: SearchResult[] = [];

  const [botConfig, worlds, places, lorebooks, sessions, collections] =
    await Promise.all([
      readBotConfig().catch(() => null),
      readWorlds().catch(() => []),
      readPlaces().catch(() => []),
      readLorebooks().catch(() => []),
      (async () => {
        try {
          const logs = await readChatLogs(500);
          return summarizeChatLogSessions(logs);
        } catch {
          return [];
        }
      })(),
      readCollections().catch(() => []),
    ]);

  if (botConfig?.characters) {
    for (const character of botConfig.characters) {
      if (
        matchesQuery(character.name, query) ||
        matchesQuery(character.id, query) ||
        matchesQuery(character.personaSummary ?? "", query) ||
        (character.tags ?? []).some((t: string) => matchesQuery(t, query))
      ) {
        results.push({
          type: "character",
          id: character.id,
          label: character.name,
          description: character.personaSummary ?? character.intro ?? "",
          link: `/admin/characters?id=${encodeURIComponent(character.id)}`,
        });
      }
    }
  }

  for (const world of worlds) {
    if (
      matchesQuery(world.name, query) ||
      matchesQuery(world.id, query) ||
      matchesQuery(world.overview ?? "", query) ||
      matchesQuery(world.characters ?? "", query) ||
      matchesQuery(world.history ?? "", query)
    ) {
      results.push({
        type: "world",
        id: world.id,
        label: world.name,
        description: world.overview?.slice(0, 200) ?? "",
        link: `/admin/worlds?id=${encodeURIComponent(world.id)}`,
      });
    }
  }

  for (const place of places) {
    if (
      matchesQuery(place.name, query) ||
      matchesQuery(place.id, query) ||
      matchesQuery(place.description ?? "", query) ||
      matchesQuery(place.atmosphere ?? "", query)
    ) {
      results.push({
        type: "place",
        id: place.id,
        label: place.name,
        description: place.description?.slice(0, 200) ?? "",
        link: `/admin/places?id=${encodeURIComponent(place.id)}`,
      });
    }
  }

  for (const lorebook of lorebooks) {
    if (
      matchesQuery(lorebook.name, query) ||
      matchesQuery(lorebook.id, query) ||
      matchesQuery(lorebook.content ?? "", query) ||
      (lorebook.keywords ?? []).some((kw: string) => matchesQuery(kw, query))
    ) {
      results.push({
        type: "lorebook",
        id: lorebook.id,
        label: lorebook.name,
        description: lorebook.content?.slice(0, 200) ?? "",
        link: `/admin/lorebooks?id=${encodeURIComponent(lorebook.id)}`,
      });
    }
  }

  for (const session of sessions) {
    if (
      matchesQuery(session.id, query) ||
      matchesQuery(session.name, query) ||
      (session.characterNames ?? []).some((n: string) => matchesQuery(n, query)) ||
      (session.chatTitles ?? []).some((t: string) => matchesQuery(t, query)) ||
      matchesQuery(session.latestAssistantContent ?? "", query) ||
      matchesQuery(session.latestUserMessage ?? "", query)
    ) {
      results.push({
        type: "session",
        id: session.id,
        label: session.name,
        description:
          session.chatTitles?.[0] ?? session.latestUserMessage?.slice(0, 200) ?? "",
        link: `/admin/chats?session=${encodeURIComponent(session.id)}`,
      });
    }
  }

  for (const collection of collections) {
    if (
      matchesQuery(collection.title, query) ||
      matchesQuery(collection.id, query) ||
      matchesQuery(collection.description ?? "", query)
    ) {
      results.push({
        type: "collection",
        id: collection.id,
        label: collection.title,
        description: collection.description?.slice(0, 200) ?? "",
        link: `/admin/collections?id=${encodeURIComponent(collection.id)}`,
      });
    }
  }

  const total = results.length;
  const truncated = results.slice(0, 50);

  return NextResponse.json({ results: truncated, total });
}
