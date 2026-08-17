"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, Pencil } from "lucide-react";
import type { ProfileData } from "@/lib/profile-store";
import { sampleProfiles } from "@/lib/chat-v2-sample";
import { getSelectedProfileId, setSelectedProfileId } from "@/lib/profile-store";

export default function ProfilePage() {
  const router = useRouter();
  const profiles = sampleProfiles.filter((p) => p.enabled).sort((a, b) => a.order - b.order);
  const [currentIdx, setCurrentIdx] = useState(0);
  const touchRef = useRef<{ startX: number; startY: number } | null>(null);

  useEffect(() => {
    const savedId = getSelectedProfileId();
    if (savedId) {
      const idx = profiles.findIndex((p) => p.id === savedId);
      if (idx >= 0) setCurrentIdx(idx);
    }
  }, [profiles]);

  const handleSelect = useCallback(
    (profile: ProfileData) => {
      setSelectedProfileId(profile.id);
      router.push("/chat-v2");
    },
    [router],
  );

  const goTo = (idx: number) => {
    setCurrentIdx(Math.max(0, Math.min(idx, profiles.length - 1)));
  };

  const profile = profiles[currentIdx];
  if (!profile) return null;

  return (
    <main className="flex min-h-dvh flex-col items-center bg-zeta-bg px-4 pb-8 pt-8">
      <h1 className="mb-6 mt-8 text-xl font-bold text-zeta-text">프로필을 선택하세요</h1>

      <div
        className="relative w-full max-w-[430px] overflow-hidden rounded-2xl"
        style={{ aspectRatio: "4/5" }}
        onTouchStart={(e) => {
          touchRef.current = { startX: e.touches[0].clientX, startY: e.touches[0].clientY };
        }}
        onTouchEnd={(e) => {
          if (!touchRef.current) return;
          const dx = e.changedTouches[0].clientX - touchRef.current.startX;
          if (Math.abs(dx) > 40) goTo(currentIdx + (dx < 0 ? 1 : -1));
          touchRef.current = null;
        }}
      >
        <img
          src={profile.imageUrl}
          alt={profile.name}
          className="size-full object-cover"
          draggable={false}
        />

        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/70 to-transparent" />

        <div className="absolute inset-x-0 bottom-0 flex flex-col items-center px-4 pb-4">
          <p className="text-2xl font-bold text-white">{profile.name}</p>
          <p className="mt-1 text-sm text-white/70">{profile.shortDescription}</p>
          <button
            aria-label="상세 설명"
            className="mt-1 text-white/50 transition hover:text-white/80"
            type="button"
          >
            <ChevronDown size={20} />
          </button>

          <div className="mt-3 flex w-full gap-2">
            <button
              aria-label="프로필 편집"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white/15 text-white transition hover:bg-white/25"
              type="button"
            >
              <Pencil size={18} />
            </button>
            <button
              className="flex h-11 flex-1 items-center justify-center rounded-lg bg-zeta-accent text-sm font-bold text-zeta-buttonText transition hover:brightness-95"
              onClick={() => handleSelect(profile)}
              type="button"
            >
              선택
            </button>
          </div>
        </div>
      </div>

      <div className="mt-5 flex gap-2">
        {profiles.map((p, i) => (
          <button
            aria-label={`프로필 ${i + 1}`}
            key={p.id}
            className={`size-2 rounded-full transition ${i === currentIdx ? "scale-110 bg-white" : "bg-white/25"}`}
            onClick={() => goTo(i)}
            type="button"
          />
        ))}
      </div>
    </main>
  );
}
