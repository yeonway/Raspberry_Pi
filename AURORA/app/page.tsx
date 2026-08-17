"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { HomeDiscover } from "@/components/chat/HomeDiscover";
import type { BotConfig, Character } from "@/types/chat";
import { characters as fallbackCharacters } from "@/lib/mock-data";

export default function HomePage() {
  const router = useRouter();
  const [characters, setCharacters] = useState<Character[]>(fallbackCharacters);

  useEffect(() => {
    let cancelled = false;

    async function loadChatbots() {
      try {
        const response = await fetch("/api/chatbots", { cache: "no-store" });
        if (!response.ok || cancelled) return;
        const config = (await response.json()) as BotConfig;
        if (!cancelled && config.characters?.length) {
          setCharacters(config.characters);
        }
      } catch { /* use fallback */ }
    }

    loadChatbots();
    return () => { cancelled = true; };
  }, []);

  return (
    <HomeDiscover
      characters={characters}
      onOpenChat={(characterId) => router.push(`/chat?character=${characterId}`)}
      onOpenProfile={() => router.push("/chat")}
      onViewChange={(view) => {
        if (view === "chat") router.push("/chat");
      }}
    />
  );
}
