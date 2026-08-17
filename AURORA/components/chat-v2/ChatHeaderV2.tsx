"use client";

import { ChevronDown, ChevronLeft, Menu } from "lucide-react";
import { useRouter } from "next/navigation";

type ChatHeaderV2Props = {
  title: string;
  modelName: string;
  onMenuClick: () => void;
};

export function ChatHeaderV2({ title, modelName, onMenuClick }: ChatHeaderV2Props) {
  const router = useRouter();

  return (
    <header className="sticky top-0 z-20 border-b border-zeta-line bg-zeta-bg/95 px-3 py-0 backdrop-blur">
      <div className="flex h-[54px] items-center gap-2">
        <button
          aria-label="뒤로 가기"
          className="grid size-9 shrink-0 place-items-center rounded-lg text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
          onClick={() => router.back()}
          type="button"
        >
          <ChevronLeft size={22} strokeWidth={2} />
        </button>

        <div className="min-w-0 flex-1">
          <h1 className="truncate text-[15px] font-bold text-zeta-text">{title}</h1>
        </div>

        <button
          aria-label="모델 선택"
          className="flex h-8 items-center gap-1 rounded-full bg-zeta-panel2 px-3 text-xs font-semibold text-zeta-muted transition hover:text-zeta-text"
          type="button"
        >
          {modelName}
          <ChevronDown size={12} />
        </button>

        <button
          aria-label="메뉴 열기"
          className="grid size-9 shrink-0 place-items-center rounded-lg text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
          onClick={onMenuClick}
          type="button"
        >
          <Menu size={20} />
        </button>
      </div>
    </header>
  );
}
