"use client";

import type { ChatV2TextMessage } from "@/types/chat-v2";
import { MessageRenderer } from "./MessageRenderer";

export function UserMessageBubble({
  message,
  userName,
}: {
  message: ChatV2TextMessage;
  userName?: string;
}) {
  return (
    <div className="flex justify-end px-2">
      <div style={{ maxWidth: "80%" }}>
        <div className="inline-block max-w-full rounded-2xl bg-zeta-userBubble px-3.5 py-2.5">
          <div className="whitespace-pre-wrap break-words text-[14px] leading-[1.65] text-zeta-userBubbleText">
            <MessageRenderer
              content={message.content}
              userName={userName}
              narrativeClass="italic opacity-75 block"
              dialogueClass="font-medium"
              plainClass=""
            />
          </div>
        </div>
      </div>
    </div>
  );
}
