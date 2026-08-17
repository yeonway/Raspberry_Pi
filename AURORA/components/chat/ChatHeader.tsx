import { Settings } from "lucide-react";
import type { Character, ChatRoom } from "@/types/chat";
import { BotAvatar } from "./BotAvatar";
import { ThemeSelector } from "./ThemeSelector";

type ChatHeaderProps = {
  character: Character;
  hasCustomCharacterPrompt?: boolean;
  room: ChatRoom;
  onEditCustomCharacterPrompt: () => void;
};

export function ChatHeader({
  character,
  hasCustomCharacterPrompt = false,
  room,
  onEditCustomCharacterPrompt,
}: ChatHeaderProps) {
  return (
    <header className="hidden min-h-14 shrink-0 items-center justify-between border-b border-zeta-line bg-zeta-panel px-6 md:flex md:px-8">
      <button
        aria-label="캐릭터 설정"
        className="flex min-w-0 items-center gap-3 rounded-lg px-2.5 py-2 text-left transition hover:bg-zeta-panel2"
        onClick={onEditCustomCharacterPrompt}
        title="캐릭터 설정"
        type="button"
      >
        <BotAvatar character={character} size="sm" />
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-zeta-text">
            {character.name}
          </h1>
          <p className="truncate text-xs text-zeta-muted">
            {hasCustomCharacterPrompt ? "대화 설정 적용 중" : room.title}
          </p>
        </div>
      </button>
      <div className="flex items-center gap-1.5">
        <ThemeSelector />
        <button
          aria-label="캐릭터 설정"
          className="inline-flex size-9 items-center justify-center rounded-full text-zeta-soft transition hover:bg-zeta-panel2 hover:text-zeta-text focus-visible:ring-2 focus-visible:ring-zeta-accent focus-visible:ring-offset-2"
          onClick={onEditCustomCharacterPrompt}
          title="캐릭터 설정"
          type="button"
        >
          <Settings size={17} />
        </button>
      </div>
    </header>
  );
}
