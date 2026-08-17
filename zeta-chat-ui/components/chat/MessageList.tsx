"use client";

import { useEffect, useRef } from "react";
import type { Character, Message } from "@/types/chat";
import { BotAvatar } from "./BotAvatar";
import { MessageBubble } from "./MessageBubble";

type MessageListProps = {
  character: Character;
  messages: Message[];
  isSending: boolean;
  onDelete: (messageId: string) => void;
  onEdit: (messageId: string, content: string) => void;
  onOpenCharacterSettings: () => void;
  onRegenerate: (messageId: string) => void;
};

export function MessageList({
  character,
  isSending,
  messages,
  onDelete,
  onEdit,
  onOpenCharacterSettings,
  onRegenerate,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const latestMessage = messages.at(-1);
  const shouldShowTypingDots =
    isSending && latestMessage?.role !== "assistant";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [latestMessage?.content, messages.length, isSending]);

  return (
    <div className="zeta-message-scroll scrollbar-thin min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-5 md:px-8">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 md:gap-3">
        {messages.map((message) => (
          <MessageBubble
            character={character}
            key={message.id}
            message={message}
            onDelete={onDelete}
            onEdit={onEdit}
            onOpenCharacterSettings={onOpenCharacterSettings}
            onRegenerate={onRegenerate}
          />
        ))}

        {shouldShowTypingDots ? (
          <div className="flex items-end gap-2">
            <button
              aria-label="캐릭터 설정"
              className="shrink-0 rounded-full outline-none transition hover:brightness-110 focus-visible:ring-2 focus-visible:ring-zeta-accent"
              onClick={onOpenCharacterSettings}
              title="캐릭터 설정"
              type="button"
            >
              <BotAvatar character={character} size="sm" />
            </button>
            <div className="flex gap-1 rounded-2xl rounded-bl-sm border border-zeta-line bg-zeta-assistantBubble px-4 py-3">
              <span className="size-2 animate-pulse rounded-full bg-zeta-soft" />
              <span className="size-2 animate-pulse rounded-full bg-zeta-soft [animation-delay:120ms]" />
              <span className="size-2 animate-pulse rounded-full bg-zeta-soft [animation-delay:240ms]" />
            </div>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
