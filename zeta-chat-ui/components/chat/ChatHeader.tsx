import { House, Settings, UserRound } from "lucide-react";
import type { Character, ChatRoom } from "@/types/chat";
import { BotAvatar } from "./BotAvatar";
import { ThemeSelector } from "./ThemeSelector";

type ChatHeaderProps = {
  character: Character;
  hasCustomCharacterPrompt?: boolean;
  room: ChatRoom;
  showAdminLink?: boolean;
  onEditCustomCharacterPrompt: () => void;
  onOpenHome?: () => void;
  onOpenAccountSettings: () => void;
};

export function ChatHeader({
  character,
  hasCustomCharacterPrompt = false,
  room,
  showAdminLink = false,
  onEditCustomCharacterPrompt,
  onOpenHome,
  onOpenAccountSettings,
}: ChatHeaderProps) {
  return (
    <header className="hidden min-h-[64px] shrink-0 items-center justify-between border-b border-zeta-line bg-zeta-panel px-4 md:flex md:px-5">
      <button
        aria-label="캐릭터 설정"
        className="flex min-w-0 items-center gap-3 rounded-lg text-left transition hover:bg-zeta-panel2"
        onClick={onEditCustomCharacterPrompt}
        title="캐릭터 설정"
        type="button"
      >
        <BotAvatar character={character} />
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-zeta-text">
            {character.name}
          </h1>
          <p className="truncate text-xs text-zeta-muted">
            {hasCustomCharacterPrompt ? "대화 설정 적용 중" : room.title}
          </p>
        </div>
      </button>

      <div className="flex items-center gap-2">
        {onOpenHome ? (
          <button
            aria-label="홈"
            className="inline-flex size-9 items-center justify-center rounded-full border border-zeta-line bg-zeta-panel text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            onClick={onOpenHome}
            title="홈"
            type="button"
          >
            <House size={16} />
          </button>
        ) : null}
        {showAdminLink ? (
          <a
            aria-label="관리자 설정"
            className="inline-flex h-9 items-center gap-1.5 rounded-full border border-zeta-line bg-zeta-panel px-3 text-xs font-semibold text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            href="/admin"
            title="관리자 설정"
          >
            <Settings size={16} />
            <span className="hidden sm:inline">관리자</span>
          </a>
        ) : null}
        <ThemeSelector className="hidden md:block" />
        <button
          aria-label="계정 설정"
          className="inline-flex h-9 items-center gap-1.5 rounded-full border border-zeta-line bg-zeta-panel px-3 text-xs font-semibold text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
          onClick={onOpenAccountSettings}
          title="계정 설정"
          type="button"
        >
          <UserRound size={16} />
          <span className="hidden sm:inline">계정</span>
        </button>
      </div>
    </header>
  );
}
