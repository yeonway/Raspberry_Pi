"use client";

import { useMemo } from "react";
import { Info } from "lucide-react";
import { sampleRoom, sampleProfiles } from "@/lib/chat-v2-sample";
import { getSelectedProfileId } from "@/lib/profile-store";
import { ChatHeaderV2 } from "@/components/chat-v2/ChatHeaderV2";
import { ChatFeedV2 } from "@/components/chat-v2/ChatFeedV2";

export default function ChatV2Page() {
  const selectedProfile = useMemo(() => {
    const profiles = sampleProfiles.filter((p) => p.enabled);
    const id = getSelectedProfileId();
    return profiles.find((p) => p.id === id);
  }, []);

  return (
    <div className="mx-auto flex min-h-dvh max-w-[500px] flex-col bg-zeta-bg text-zeta-text">
      <ChatHeaderV2
        title={sampleRoom.title}
        modelName={sampleRoom.modelName}
        onMenuClick={() => {}}
      />

      <div className="flex items-center justify-center gap-1.5 py-2">
        <Info size={13} className="text-zeta-soft/60" />
        <p className="text-[11px] text-zeta-soft/60">답변은 모두 AI가 생성한 내용이에요</p>
      </div>

      <ChatFeedV2
        items={sampleRoom.feedItems}
        characters={sampleRoom.characters}
        userName={selectedProfile?.name}
      />
    </div>
  );
}
