"use client";

import { useState } from "react";
import { Calendar, ChevronDown, ChevronUp, Clock, MapPin } from "lucide-react";
import type { ChatV2SceneInfo } from "@/types/chat-v2";

export function SceneInfoPanel({ item }: { item: ChatV2SceneInfo }) {
  const [open, setOpen] = useState(!item.collapsed);

  return (
    <div className="-mx-2 rounded-lg border border-zeta-line bg-zeta-panel2/60 p-4">
      <button
        className="flex w-full items-center gap-2 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        {open ? (
          <ChevronUp size={16} className="text-zeta-soft" />
        ) : (
          <ChevronDown size={16} className="text-zeta-soft" />
        )}
        <span className="text-xs font-medium text-zeta-muted">장면 정보</span>
      </button>
      {open ? (
        <div className="mt-3 space-y-2">
          {item.date ? (
            <div className="flex items-center gap-2 text-sm">
              <Calendar size={15} className="text-zeta-soft" />
              <span className="font-medium text-zeta-soft">날짜</span>
              <span className="text-zeta-text">{item.date}</span>
            </div>
          ) : null}
          {item.time ? (
            <div className="flex items-center gap-2 text-sm">
              <Clock size={15} className="text-zeta-soft" />
              <span className="font-medium text-zeta-soft">시간</span>
              <span className="text-zeta-text">{item.time}</span>
            </div>
          ) : null}
          {item.location ? (
            <div className="flex items-center gap-2 text-sm">
              <MapPin size={15} className="text-zeta-soft" />
              <span className="font-medium text-zeta-soft">장소</span>
              <span className="text-zeta-text">{item.location}</span>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
