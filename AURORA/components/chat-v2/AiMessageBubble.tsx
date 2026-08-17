"use client";

import type { ChatV2Character, ChatV2TextMessage } from "@/types/chat-v2";
import { MessageRenderer } from "./MessageRenderer";

export function AiMessageBubble({
  message,
  character,
  userName,
}: {
  message: ChatV2TextMessage;
  character?: ChatV2Character;
  userName?: string;
}) {
  const char = character ?? { id: "unknown", name: "???" };

  return (
    <div className="flex gap-2.5 px-2" style={{ maxWidth: "100%" }}>
      <div className="mt-0.5 size-7 shrink-0 overflow-hidden rounded-full bg-zeta-panel2">
        {char.avatarUrl ? (
          <img
            src={char.avatarUrl}
            alt={char.name}
            className="size-full object-cover"
            width={28}
            height={28}
          />
        ) : (
          <div className="flex size-full items-center justify-center text-[11px] font-bold text-zeta-text">
            {char.name.slice(0, 1)}
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1" style={{ maxWidth: "82%" }}>
        <p className="mb-1 text-[12px] font-medium" style={{ color: char.nameColor ?? "var(--zeta-muted)" }}>
          {char.name}
        </p>
        <div className="inline-block max-w-full rounded-2xl bg-zeta-panel2 px-3.5 py-2.5">
          <div className="whitespace-pre-wrap break-words text-[14px] leading-[1.65]">
            <MessageRenderer
              content={message.content}
              userName={userName}
              narrativeClass="italic text-zeta-soft block"
              dialogueClass="text-zeta-text font-medium"
              plainClass="text-zeta-text"
            />
          </div>
        </div>
        {message.providerLabel ? (
          <p className="mt-0.5 text-[10px] text-zeta-soft/50">{message.providerLabel}</p>
        ) : null}
      </div>
    </div>
  );
}
