"use client";

import { ChevronDown, ChevronLeft, Menu } from "lucide-react";
import type { Character, ChatRoom } from "@/types/chat";
import { BotAvatar } from "./BotAvatar";

type MobileNavProps = {
  character: Character;
  hasCustomCharacterPrompt?: boolean;
  room: ChatRoom;
  onEditCustomCharacterPrompt: () => void;
  onOpenHome?: () => void;
  onOpenAccountSettings: () => void;
  onOpenRooms: () => void;
};

export function MobileNav({
  character,
  hasCustomCharacterPrompt = false,
  room,
  onEditCustomCharacterPrompt,
  onOpenHome,
  onOpenAccountSettings,
  onOpenRooms,
}: MobileNavProps) {
  return (
    <div className="zeta-mobile-shell shrink-0 md:hidden">
      <div className="flex h-12 items-center border-b border-white/10 px-3">
        <button
          aria-label="홈으로 이동"
          className="grid size-8 shrink-0 place-items-center text-zinc-200"
          onClick={onOpenHome}
          type="button"
        >
          <ChevronLeft size={22} strokeWidth={2.1} />
        </button>
        <button
          aria-label="캐릭터 설정"
          className="min-w-0 flex-1 px-1 text-left"
          onClick={onEditCustomCharacterPrompt}
          type="button"
        >
          <span className="block truncate text-[13px] font-semibold tracking-[-0.03em] text-zinc-100">
            {room.title === "새 대화" ? `${character.name}와의 대화` : room.title}
          </span>
        </button>
        <button
          aria-label="대화 모델 선택"
          className="mr-2 inline-flex h-7 items-center gap-0.5 rounded-full bg-zinc-700 px-2 text-[10px] font-semibold text-zinc-100"
          onClick={onOpenAccountSettings}
          type="button"
        >
          zeta <ChevronDown size={12} />
        </button>
      <button
        aria-label="채팅 목록 열기"
        className="grid size-8 shrink-0 place-items-center text-zinc-200"
        onClick={onOpenRooms}
        type="button"
      >
        <Menu size={20} />
      </button>
      </div>

      <div className="mx-3 mt-2 flex items-center gap-2 rounded-md bg-zinc-900 px-3 py-2 text-[10px] text-zinc-300">
        <BotAvatar character={character} size="sm" className="size-5 border-0 text-[8px]" />
        <span className="min-w-0 flex-1 truncate">캐릭터와 더 깊은 이야기를 나눠보세요</span>
        <ChevronDown size={13} className="rotate-[-90deg] text-zinc-500" />
      </div>
      <p className="py-2 text-center text-[10px] text-zinc-500">눈 뜨는 모든 것이 생명인 밤이었다</p>
      <button
        aria-label="캐릭터 설정"
        className="flex w-full items-start gap-2 border-b border-white/5 px-3 pb-3 text-left"
        onClick={onEditCustomCharacterPrompt}
        type="button"
      >
        <BotAvatar character={character} size="sm" className="mt-0.5 size-7 text-[9px]" />
        <span className="min-w-0">
          <span className="block text-[10px] text-zinc-400"># {hasCustomCharacterPrompt ? "대화 설정 적용 중" : "공포, 판타지, 소꿉친구"}</span>
          <strong className="mt-0.5 block truncate text-[13px] font-semibold text-zinc-100">{character.name}</strong>
          <span className="mt-0.5 block line-clamp-2 text-[10px] leading-4 text-zinc-400">{character.intro}</span>
        </span>
      </button>
    </div>
  );
}
