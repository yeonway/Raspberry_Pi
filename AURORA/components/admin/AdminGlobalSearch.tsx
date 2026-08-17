"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Search,
  Hash,
  X,
  ArrowRight,
  Globe,
  Users,
  MessageSquare,
  Bot,
  BookOpen,
  MapPin,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchResult {
  id: string;
  type: string;
  label: string;
  description?: string;
  link: string;
}

const typeConfig: Record<string, { icon: React.ElementType; color: string }> = {
  캐릭터: { icon: Bot, color: "text-purple-500 bg-purple-50 dark:bg-purple-900/20" },
  세계관: { icon: Globe, color: "text-blue-500 bg-blue-50 dark:bg-blue-900/20" },
  장소: { icon: MapPin, color: "text-teal-500 bg-teal-50 dark:bg-teal-900/20" },
  로어북: { icon: BookOpen, color: "text-amber-500 bg-amber-50 dark:bg-amber-900/20" },
  대화: { icon: MessageSquare, color: "text-green-500 bg-green-50 dark:bg-green-900/20" },
  사용자: { icon: Users, color: "text-slate-500 bg-slate-50 dark:bg-slate-800" },
  컬렉션: { icon: Hash, color: "text-rose-500 bg-rose-50 dark:bg-rose-900/20" },
};

interface Props {
  onNavigate?: (section: string) => void;
}

export default function AdminGlobalSearch({ onNavigate }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/admin/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setResults(data.results ?? data ?? []);
      setOpen(true);
      setSelectedIndex(-1);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(query), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, search]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey && e.key === "k") || (e.key === "/" && document.activeElement !== inputRef.current)) {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === "Escape") {
        setOpen(false);
        inputRef.current?.blur();
      }
      if (e.key === "ArrowDown" && open) {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
      }
      if (e.key === "ArrowUp" && open) {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, -1));
      }
      if (e.key === "Enter" && open && selectedIndex >= 0) {
        const r = results[selectedIndex];
        if (r) handleSelect(r);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, results, selectedIndex]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(result: SearchResult) {
    onNavigate?.(result.link);
    setOpen(false);
    setQuery("");
    setResults([]);
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zeta-muted" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results.length > 0) setOpen(true);
          }}
          placeholder="검색..."
          className="zeta-input w-full pl-9 pr-16 py-2 text-sm rounded-lg"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded text-[10px] bg-zeta-muted/10 text-zeta-muted border border-zeta-border">
          Ctrl+K
        </kbd>
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setResults([]);
              setOpen(false);
            }}
            className="absolute right-14 top-1/2 -translate-y-1/2 text-zeta-muted hover:text-zeta-text"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {open && (
        <div className="absolute top-full mt-1 w-full z-50 zeta-card shadow-xl max-h-80 overflow-auto rounded-lg border border-zeta-border">
          {loading && (
            <div className="p-4 text-center text-sm text-zeta-muted">검색 중...</div>
          )}
          {!loading && results.length === 0 && (
            <div className="p-4 text-center text-sm text-zeta-muted">결과가 없습니다.</div>
          )}
          {!loading &&
            results.map((r, i) => {
              const cfg = typeConfig[r.type] ?? { icon: Hash, color: "text-gray-500 bg-gray-50 dark:bg-gray-800" };
              const Icon = cfg.icon;
              return (
                <button
                  key={r.id}
                  onClick={() => handleSelect(r)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 text-left transition-colors",
                    i === selectedIndex
                      ? "bg-zeta-accent/10"
                      : "hover:bg-zeta-hover"
                  )}
                >
                  <div className={cn("p-1.5 rounded-lg shrink-0", cfg.color)}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-zeta-text truncate">{r.label}</p>
                    {r.description && (
                      <p className="text-xs text-zeta-muted truncate">{r.description}</p>
                    )}
                  </div>
                  <span className="text-xs text-zeta-muted shrink-0">{r.type}</span>
                  <ArrowRight className="w-3 h-3 text-zeta-muted shrink-0" />
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}
