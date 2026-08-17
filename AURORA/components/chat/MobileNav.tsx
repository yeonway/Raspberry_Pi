"use client";

import { ChevronLeft, Menu } from "lucide-react";
import type { Character } from "@/types/chat";
import { BotAvatar } from "./BotAvatar";

type MobileNavProps = {
  character: Character;
  onOpenHome?: () => void;
  onOpenRooms: () => void;
};

export function MobileNav({
  character,
  onOpenHome,
  onOpenRooms,
}: MobileNavProps) {
  return (
    <div className="zeta-mobile-shell shrink-0 md:hidden">
      <div className="flex h-12 items-center border-b border-zeta-line px-3">
        {onOpenHome ? (
          <button
            aria-label="홈으로"
            className="grid size-9 shrink-0 place-items-center rounded-lg text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            onClick={onOpenHome}
            type="button"
          >
            <ChevronLeft size={22} strokeWidth={2} />
          </button>
        ) : null}
        <button
          aria-label="캐릭터 정보"
          className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg px-2 py-1 text-left transition hover:bg-zeta-panel2"
          type="button"
        >
          <BotAvatar character={character} size="sm" className="size-7 text-[8px]" />
          <span className="min-w-0 truncate text-sm font-semibold text-zeta-text">
            {character.name}
          </span>
        </button>
        <button
          aria-label="메뉴 열기"
          className="grid size-9 shrink-0 place-items-center rounded-lg text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
          onClick={onOpenRooms}
          type="button"
        >
          <Menu size={20} />
        </button>
      </div>
    </div>
  );
}
