"use client";

import type React from "react";
import Image from "next/image";
import {
  Home,
  MessageCircle,
  Plus,
  Sparkles,
  UserRound,
} from "lucide-react";
import type { Character } from "@/types/chat";
import { cn } from "@/lib/utils";

type HomeDiscoverProps = {
  characters: Character[];
  onOpenChat: (characterId: string) => void;
  onOpenProfile: () => void;
  onViewChange: (view: "chat" | "home") => void;
};

function formatTags(character: Character) {
  return character.tags
    .flatMap((tag) => tag.split(/\s+/))
    .filter(Boolean)
    .slice(0, 3)
    .join(" ");
}

export function HomeDiscover({
  characters,
  onOpenChat,
  onOpenProfile,
  onViewChange,
}: HomeDiscoverProps) {
  return (
    <main className="home-discover min-h-dvh bg-zeta-bg pb-24 text-zeta-text">
      <header className="sticky top-0 z-20 border-b border-zeta-line bg-zeta-bg/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl bg-zeta-accent text-zeta-buttonText">
              <Sparkles size={17} />
            </div>
            <span className="text-base font-bold tracking-[-0.03em] text-zeta-text">AURORA</span>
            <span className="hidden text-xs text-zeta-soft sm:inline">캐릭터 챗봇</span>
          </div>
          <button
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-zeta-accent px-4 text-sm font-semibold text-zeta-buttonText transition hover:brightness-95"
            onClick={() => onViewChange("chat")}
            type="button"
          >
            <MessageCircle size={16} />
            채팅 열기
          </button>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 pt-4 sm:px-8 sm:pt-6">
        <div className="grid grid-cols-2 gap-3 pb-6 sm:grid-cols-3 lg:grid-cols-4 sm:gap-5">
          {characters.map((character) => (
            <button
              className="group overflow-hidden rounded-2xl bg-zeta-panel2 text-left shadow-zeta transition hover:-translate-y-1 hover:brightness-110 focus-visible:ring-2 focus-visible:ring-zeta-accent focus-visible:ring-offset-2"
              key={character.id}
              onClick={() => onOpenChat(character.id)}
              type="button"
            >
              <div className="relative aspect-[.67] overflow-hidden bg-gradient-to-br from-zeta-muted via-zeta-panel2 to-zeta-bg">
                {character.avatarImageUrl ? (
                  <Image
                    alt={`${character.name} 캐릭터 이미지`}
                    className="object-cover transition duration-300 group-hover:scale-105"
                    fill
                    sizes="(max-width: 640px) 45vw, (max-width: 1024px) 28vw, 220px"
                    src={character.avatarImageUrl}
                    unoptimized
                  />
                ) : (
                  <div className={cn("absolute inset-0 bg-gradient-to-br", character.coverGradient)} />
                )}
                <div className="absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-zeta-panel2 via-zeta-panel2/15 to-transparent" />
              </div>
              <div className="-mt-20 relative min-h-36 p-4">
                <h2 className="truncate text-lg font-bold tracking-[-0.04em] text-zeta-text">{character.name}</h2>
                <p className="mt-2 line-clamp-2 text-sm leading-5 text-zeta-muted">{character.intro}</p>
                <p className="mt-3 truncate text-xs text-zeta-soft">{formatTags(character) || "#새로운이야기"}</p>
              </div>
            </button>
          ))}
        </div>

        {!characters.length ? <p className="py-16 text-center text-sm text-zeta-muted">캐릭터가 없어요.</p> : null}
      </section>

      <nav aria-label="하단 메뉴" className="fixed inset-x-0 bottom-0 z-30 border-t border-zeta-line bg-zeta-panel/95 px-4 pb-[max(0.55rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur md:hidden">
        <div className="mx-auto grid max-w-md grid-cols-4">
          <BottomNavButton active icon={<Home size={25} fill="currentColor" />} label="홈" onClick={() => onViewChange("home")} />
          <BottomNavButton icon={<MessageCircle size={25} />} label="대화" onClick={() => onViewChange("chat")} />
          <BottomNavButton icon={<Plus size={26} strokeWidth={3} />} label="제작" onClick={() => onOpenChat(characters[0]?.id ?? "")} />
          <BottomNavButton icon={<UserRound size={25} fill="currentColor" />} label="마이페이지" onClick={onOpenProfile} />
        </div>
      </nav>
    </main>
  );
}

function BottomNavButton({ active = false, icon, label, onClick }: { active?: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return <button className={cn("flex flex-col items-center gap-1 py-1 text-[11px] font-medium transition", active ? "text-zeta-text" : "text-zeta-soft")} onClick={onClick} type="button"><span>{icon}</span>{label}</button>;
}
