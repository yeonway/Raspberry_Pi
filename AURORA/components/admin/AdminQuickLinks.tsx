"use client";

import { useState, useRef, useEffect } from "react";
import {
  ChevronDown,
  Plus,
  Globe,
  MapPin,
  BookOpen,
  FlaskConical,
  MessageSquare,
  HardDrive,
  Bug,
  Trash2,
  Search,
  BarChart3,
  Database,
  StickyNote,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface QuickLink {
  label: string;
  icon: React.ElementType;
  section: string;
}

const groups: { name: string; items: QuickLink[] }[] = [
  {
    name: "생성",
    items: [
      { label: "새 캐릭터", icon: Plus, section: "#character-create" },
      { label: "새 플롯", icon: Plus, section: "#plot-create" },
      { label: "새 세계관", icon: Globe, section: "#world-create" },
      { label: "새 장소", icon: MapPin, section: "#place-create" },
      { label: "새 로어북", icon: BookOpen, section: "#lorebook-create" },
    ],
  },
  {
    name: "도구",
    items: [
      { label: "AI 테스트실", icon: FlaskConical, section: "#test-lab" },
      { label: "대화 감사", icon: MessageSquare, section: "#conversation-audit" },
      { label: "백업", icon: HardDrive, section: "#backup" },
      { label: "오류 로그", icon: Bug, section: "#error-log" },
      { label: "휴지통", icon: Trash2, section: "#trash" },
    ],
  },
  {
    name: "분석",
    items: [
      { label: "검색", icon: Search, section: "#search" },
      { label: "통계", icon: BarChart3, section: "#statistics" },
      { label: "데이터 현황", icon: Database, section: "#data-overview" },
      { label: "메모장", icon: StickyNote, section: "#notepad" },
      { label: "로그", icon: FileText, section: "#logs" },
    ],
  },
];

interface Props {
  onNavigate: (section: string) => void;
}

export default function AdminQuickLinks({ onNavigate }: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(section: string) {
    onNavigate(section);
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="zeta-btn zeta-btn-ghost text-sm"
      >
        빠른 이동
        <ChevronDown
          className={cn("w-4 h-4 ml-1 transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 zeta-card shadow-xl w-64 max-h-96 overflow-auto rounded-lg border border-zeta-border">
          {groups.map((group) => (
            <div key={group.name} className="py-1">
              <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-zeta-muted">
                {group.name}
              </p>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.label}
                    onClick={() => handleSelect(item.section)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-zeta-text hover:bg-zeta-hover transition-colors text-left"
                  >
                    <Icon className="w-4 h-4 text-zeta-muted shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
