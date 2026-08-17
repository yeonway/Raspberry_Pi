"use client";

import { useEffect, useRef } from "react";
import type { ChatV2Character, ChatV2FeedItem } from "@/types/chat-v2";
import { AiMessageBubble } from "./AiMessageBubble";
import { UserMessageBubble } from "./UserMessageBubble";
import { GeneratedImageCard } from "./GeneratedImageCard";
import { SceneInfoPanel } from "./SceneInfoPanel";

export function ChatFeedV2({
  items,
  characters,
  userName,
}: {
  items: ChatV2FeedItem[];
  characters: ChatV2Character[];
  userName?: string;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, []);

  const getChar = (id?: string) => characters.find((c) => c.id === id);

  return (
    <div className="flex flex-col gap-4 px-2 py-4">
      {items.map((item) => {
        switch (item.type) {
          case "message":
            if (item.sender === "ai") {
              return (
                <AiMessageBubble
                  key={item.id}
                  message={item}
                  character={getChar(item.characterId)}
                  userName={userName}
                />
              );
            }
            return (
              <UserMessageBubble
                key={item.id}
                message={item}
                userName={userName}
              />
            );

          case "image":
            return <GeneratedImageCard key={item.id} item={item} />;

          case "sceneInfo":
            return <SceneInfoPanel key={item.id} item={item} />;

          case "system":
            return (
              <p
                key={item.id}
                className="text-center text-[11px] text-zeta-soft"
              >
                {item.content}
              </p>
            );

          case "typing":
            return (
              <div key={item.id} className="flex gap-2.5 px-2">
                <div className="mt-0.5 size-7 shrink-0 rounded-full bg-zeta-panel2" />
                <div className="flex items-center gap-1 rounded-2xl bg-zeta-panel2 px-4 py-3">
                  <span className="size-1.5 animate-bounce rounded-full bg-zeta-soft" />
                  <span className="size-1.5 animate-bounce rounded-full bg-zeta-soft [animation-delay:0.1s]" />
                  <span className="size-1.5 animate-bounce rounded-full bg-zeta-soft [animation-delay:0.2s]" />
                </div>
              </div>
            );

          default:
            return null;
        }
      })}
      <div ref={bottomRef} />
    </div>
  );
}
