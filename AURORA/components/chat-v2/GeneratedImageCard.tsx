"use client";

import { useState } from "react";
import { ImageOff, Maximize2, X } from "lucide-react";
import type { ChatV2GeneratedImage } from "@/types/chat-v2";

export function GeneratedImageCard({ item }: { item: ChatV2GeneratedImage }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const ar = item.aspectRatio ?? 1.5;

  if (item.generationStatus === "failed" || error) {
    return (
      <div className="-mx-2 flex min-h-[200px] items-center justify-center rounded-lg bg-zeta-panel2/60 px-4">
        <div className="text-center">
          <ImageOff size={28} className="mx-auto text-zeta-soft" />
          <p className="mt-2 text-xs text-zeta-muted">이미지를 불러오지 못했습니다</p>
        </div>
      </div>
    );
  }

  const isGenerating = item.generationStatus === "generating";

  return (
    <>
      <div className="relative -mx-2 overflow-hidden rounded-lg" style={{ aspectRatio: ar }}>
        {!loaded ? (
          <div className="absolute inset-0 flex items-center justify-center bg-zeta-panel2">
            <div className="text-center">
              <div className="mx-auto size-8 animate-pulse rounded-full bg-zeta-panel" />
              <p className="mt-2 text-xs text-zeta-soft">
                {isGenerating ? "이미지 생성 중..." : "불러오는 중..."}
              </p>
            </div>
          </div>
        ) : null}
        <img
          src={item.imageUrl}
          alt={item.alt ?? ""}
          className="size-full object-cover"
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
          style={{ opacity: loaded ? 1 : 0 }}
        />
        {loaded ? (
          <button
            aria-label="이미지 확대"
            className="absolute right-2 top-2 rounded-full bg-black/50 p-1.5 text-white/80 transition hover:bg-black/70"
            onClick={() => setFullscreen(true)}
            type="button"
          >
            <Maximize2 size={16} />
          </button>
        ) : null}
      </div>

      {fullscreen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={() => setFullscreen(false)}
        >
          <button
            aria-label="닫기"
            className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white transition hover:bg-white/20"
            onClick={() => setFullscreen(false)}
            type="button"
          >
            <X size={22} />
          </button>
          <img
            src={item.imageUrl}
            alt={item.alt ?? ""}
            className="max-h-full max-w-full rounded-lg object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      ) : null}
    </>
  );
}
