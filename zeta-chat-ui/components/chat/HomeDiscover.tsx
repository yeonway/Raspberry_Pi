"use client";

import type React from "react";
import Image from "next/image";
import {
  Bell,
  ChevronDown,
  Eye,
  Heart,
  Home,
  MessageCircle,
  Plus,
  Search,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import type { Character } from "@/types/chat";
import { cn } from "@/lib/utils";

type HomeDiscoverProps = {
  characters: Character[];
  onOpenChat: (characterId: string) => void;
  onOpenProfile: () => void;
  onViewChange: (view: "chat" | "home") => void;
};

const categories = ["전체", "연애·관계", "성장·모험", "미스터리·스릴러", "일상"];
const primaryTabs = [
  "콘테스트",
  "홈",
  "랭킹",
  "퀴즈",
];

function cardCategory(character: Character) {
  const tags = character.tags.join(" ");
  if (/공포|미스터리|스릴러|추리/.test(tags)) return "미스터리·스릴러";
  if (/성장|모험|판타지/.test(tags)) return "성장·모험";
  if (/연애|관계|로맨스|소꿉|짝사랑/.test(tags)) return "연애·관계";
  return "일상";
}

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
  const [activeCategory, setActiveCategory] = useState("전체");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [isNotified, setIsNotified] = useState(true);
  const [activePrimaryTab, setActivePrimaryTab] = useState("콘테스트");

  const visibleCharacters = characters.filter((character) => {
    const inCategory =
      activeCategory === "전체" || cardCategory(character) === activeCategory;
    const normalizedQuery = query.trim().toLocaleLowerCase("ko-KR");
    const matchesQuery =
      !normalizedQuery ||
      [character.name, character.intro, character.tags.join(" ")]
        .join(" ")
        .toLocaleLowerCase("ko-KR")
        .includes(normalizedQuery);
    return inCategory && matchesQuery;
  });
  const featuredCharacters =
    visibleCharacters.length >= 4
      ? visibleCharacters
      : Array.from({ length: Math.max(visibleCharacters.length, 4) }, (_, index) =>
          visibleCharacters[index % visibleCharacters.length],
        ).filter((character): character is Character => Boolean(character));

  return (
    <main className="home-discover min-h-dvh bg-[#121212] pb-24 text-zeta-text">
      <header className="sticky top-0 z-20 border-b border-white/5 bg-[#121212]/95 backdrop-blur">
        <div className="mx-auto flex h-[72px] max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
          <nav aria-label="주요 메뉴" className="flex min-w-0 items-center gap-5 sm:gap-7">
            {primaryTabs.map((label) => (
              <button
                className={cn(
                  "shrink-0 text-lg font-bold tracking-[-0.04em] transition sm:text-xl",
                  activePrimaryTab === label
                    ? "text-white"
                    : "text-zinc-600 hover:text-zinc-300",
                )}
                key={label}
                onClick={() => {
                  setActivePrimaryTab(label);
                  if (label === "홈") onViewChange("home");
                }}
                type="button"
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-3">
            <button
              aria-label="검색"
              className="grid size-10 place-items-center rounded-full text-white transition hover:bg-white/10"
              onClick={() => setIsSearchOpen((open) => !open)}
              type="button"
            >
              <Search size={27} strokeWidth={2.2} />
            </button>
            <button
              aria-label="알림"
              className="relative grid size-10 place-items-center rounded-full text-white transition hover:bg-white/10"
              onClick={() => setIsNotified(false)}
              type="button"
            >
              <Bell size={25} strokeWidth={2.1} />
              {isNotified ? <span className="absolute right-1 top-1 size-2 rounded-full bg-red-500" /> : null}
            </button>
          </div>
        </div>
        {isSearchOpen ? (
          <div className="mx-auto max-w-6xl px-5 pb-4 sm:px-8">
            <label className="flex h-11 items-center gap-2 rounded-xl bg-zinc-800 px-3 text-zinc-400">
              <Search size={18} />
              <input
                autoFocus
                className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-zinc-500"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="캐릭터 또는 태그 검색"
                type="search"
                value={query}
              />
            </label>
          </div>
        ) : null}
      </header>

      <section className="mx-auto max-w-6xl px-5 pt-6 sm:px-8">
        <div className="flex items-center gap-5 border-b border-zinc-800 pb-4 text-lg font-bold">
          <span className="relative text-white after:absolute after:-bottom-[17px] after:left-0 after:h-0.5 after:w-full after:bg-white">전체 보기</span>
          <span className="text-zinc-500">큐레이션</span>
        </div>

        <div className="scrollbar-thin -mx-5 mt-3 flex gap-2 overflow-x-auto px-5 pb-2 sm:-mx-8 sm:px-8">
          <button className="inline-flex h-10 shrink-0 items-center gap-1 px-1 text-sm font-semibold text-zinc-400" type="button">
            추천순 <ChevronDown size={16} />
          </button>
          <span className="my-2 h-5 w-px shrink-0 bg-zinc-700" />
          {categories.map((category) => (
            <button
              className={cn(
                "h-10 shrink-0 rounded-full px-4 text-sm font-semibold transition",
                activeCategory === category
                  ? "bg-violet-600 text-white shadow-[0_0_22px_rgba(124,58,237,0.35)]"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200",
              )}
              key={category}
              onClick={() => setActiveCategory(category)}
              type="button"
            >
              {category}
            </button>
          ))}
        </div>

        <button
          className="relative mt-7 flex min-h-32 w-full overflow-hidden rounded-2xl border border-violet-400/25 bg-gradient-to-r from-[#2e176e] via-[#3d208c] to-[#1b1558] px-6 text-left shadow-[0_12px_28px_rgba(47,24,111,.32)] transition hover:brightness-110 sm:min-h-40 sm:px-10"
          onClick={() => setActiveCategory("전체")}
          type="button"
        >
          <span className="absolute -left-8 -top-12 size-48 rounded-full border border-violet-300/40" />
          <span className="absolute right-4 top-3 text-3xl text-violet-200/80">✦</span>
          <span className="relative my-auto block">
            <strong className="block text-xl tracking-[-0.04em] text-white sm:text-3xl">지금 전세계가 주목하는 플롯</strong>
            <span className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-violet-100 sm:text-lg">글로벌 큐레이션 보러가기 <Eye size={18} /></span>
          </span>
        </button>

        <div className="mt-7 grid grid-cols-2 gap-3 pb-6 sm:grid-cols-3 lg:grid-cols-4 sm:gap-5">
          {featuredCharacters.map((character, index) => (
            <button
              className="group overflow-hidden rounded-2xl bg-[#222225] text-left shadow-[0_8px_22px_rgba(0,0,0,.22)] transition hover:-translate-y-1 hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400"
              key={`${character.id}-${index}`}
              onClick={() => onOpenChat(character.id)}
              type="button"
            >
              <div className="relative aspect-[.67] overflow-hidden bg-gradient-to-br from-zinc-600 via-zinc-800 to-zinc-950">
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
                <div className="absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-[#222225] via-[#222225]/15 to-transparent" />
                <span className="absolute left-2 top-2 grid size-7 place-items-center rounded-lg bg-violet-600 text-xs font-black text-white">N</span>
                <span className="absolute left-10 top-2 inline-flex h-7 items-center gap-1 rounded-lg bg-zinc-900/75 px-2 text-[11px] font-semibold text-zinc-200"><Heart size={12} fill="currentColor" /> {index === 0 ? "7.5만" : `${index + 1}.2만`}</span>
                <span className="absolute -right-7 top-3 rotate-45 bg-fuchsia-500 px-8 py-1 text-[10px] font-black text-white">콘테스트</span>
              </div>
              <div className="-mt-20 relative min-h-36 p-4">
                <h2 className="truncate text-lg font-bold tracking-[-0.04em] text-white">{character.name}</h2>
                <p className="mt-2 line-clamp-2 text-sm leading-5 text-zinc-200">{character.intro}</p>
                <p className="mt-3 truncate text-xs text-zinc-500">{formatTags(character) || "#새로운이야기"}</p>
              </div>
            </button>
          ))}
        </div>

        {!visibleCharacters.length ? <p className="py-16 text-center text-sm text-zinc-500">조건에 맞는 캐릭터가 없어요.</p> : null}
      </section>

      <nav aria-label="하단 메뉴" className="fixed inset-x-0 bottom-0 z-30 border-t border-white/5 bg-[#171717]/95 px-4 pb-[max(0.55rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur md:hidden">
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
  return <button className={cn("flex flex-col items-center gap-1 py-1 text-[11px] font-medium", active ? "text-white" : "text-zinc-500")} onClick={onClick} type="button"><span>{icon}</span>{label}</button>;
}
