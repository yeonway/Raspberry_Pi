"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  History,
  Filter,
  ChevronDown,
  ChevronRight,
  GitCompare,
  Clock,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Category =
  | "전체"
  | "캐릭터"
  | "세계관"
  | "프롬프트"
  | "AI"
  | "메모리"
  | "운영";

interface AuditEntry {
  id: string;
  timestamp: string;
  category: Exclude<Category, "전체">;
  action: string;
  target: string;
  user?: string;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
}

const CATEGORIES: Category[] = [
  "전체",
  "캐릭터",
  "세계관",
  "프롬프트",
  "AI",
  "메모리",
  "운영",
];

const CATEGORY_COLORS: Record<string, string> = {
  캐릭터: "zeta-bg-blue-100 zeta-text-blue-700 dark:zeta-bg-blue-900 dark:zeta-text-blue-200",
  세계관: "zeta-bg-green-100 zeta-text-green-700 dark:zeta-bg-green-900 dark:zeta-text-green-200",
  프롬프트: "zeta-bg-purple-100 zeta-text-purple-700 dark:zeta-bg-purple-900 dark:zeta-text-purple-200",
  AI: "zeta-bg-amber-100 zeta-text-amber-700 dark:zeta-bg-amber-900 dark:zeta-text-amber-200",
  메모리: "zeta-bg-cyan-100 zeta-text-cyan-700 dark:zeta-bg-cyan-900 dark:zeta-text-cyan-200",
  운영: "zeta-bg-gray-100 zeta-text-gray-600 dark:zeta-bg-gray-800 dark:zeta-text-gray-300",
};

function useAuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/admin/config")
      .then((r) => r.json())
      .then((data) => {
        const log = data.auditLog || [];
        setEntries(
          log.sort(
            (a: AuditEntry, b: AuditEntry) =>
              new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
          )
        );
      })
      .catch(() => setEntries([]))
      .finally(() => setLoading(false));
  }, []);

  return { entries, loading };
}

function DiffView({ before, after }: { before?: Record<string, unknown>; after?: Record<string, unknown> }) {
  if (!before && !after) return <span className="zeta-text-xs zeta-text-zeta-text-tertiary">변경 내용 없음</span>;

  const allKeys = Array.from(
    new Set([...(Object.keys(before || {})), ...(Object.keys(after || {}))])
  );

  return (
    <div className="zeta-space-y-1">
      {allKeys.map((key) => {
        const bVal = before?.[key];
        const aVal = after?.[key];
        const bStr = typeof bVal === "object" ? JSON.stringify(bVal, null, 2) : String(bVal ?? "—");
        const aStr = typeof aVal === "object" ? JSON.stringify(aVal, null, 2) : String(aVal ?? "—");
        const changed = bStr !== aStr;

        return (
          <div key={key} className="zeta-text-xs">
            <span className="zeta-font-medium zeta-text-zeta-text">{key}:</span>
            <div className="zeta-grid zeta-grid-cols-2 zeta-gap-2 zeta-mt-0.5">
              <div
                className={cn(
                  "zeta-p-1.5 zeta-rounded zeta-font-mono zeta-text-xs zeta-overflow-x-auto zeta-whitespace-pre-wrap",
                  changed ? "zeta-bg-red-50 dark:zeta-bg-red-950 zeta-text-red-700 dark:zeta-text-red-300" : "zeta-bg-zeta-bg-secondary zeta-text-zeta-text-tertiary"
                )}
              >
                {bStr}
              </div>
              <div
                className={cn(
                  "zeta-p-1.5 zeta-rounded zeta-font-mono zeta-text-xs zeta-overflow-x-auto zeta-whitespace-pre-wrap",
                  changed ? "zeta-bg-green-50 dark:zeta-bg-green-950 zeta-text-green-700 dark:zeta-text-green-300" : "zeta-bg-zeta-bg-secondary zeta-text-zeta-text-tertiary"
                )}
              >
                {aStr}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AdminAuditLog() {
  const { entries, loading } = useAuditLog();
  const [category, setCategory] = useState<Category>("전체");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const filtered = useMemo(() => {
    if (category === "전체") return entries;
    return entries.filter((e) => e.category === category);
  }, [entries, category]);

  const toggleExpand = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  }, []);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  if (loading) return <p className="zeta-text-sm zeta-text-zeta-text-tertiary zeta-p-4">로딩 중...</p>;

  return (
    <div className="zeta-space-y-4">
      <div className="zeta-flex zeta-items-center zeta-gap-3">
        <History className="zeta-w-4 zeta-h-4 zeta-text-zeta-text-secondary" />
        <div className="zeta-flex zeta-gap-1 zeta-bg-zeta-bg-secondary zeta-rounded-lg zeta-p-1 zeta-flex-wrap">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={cn(
                "zeta-px-2.5 zeta-py-1 zeta-text-xs zeta-rounded-md zeta-transition-colors zeta-flex zeta-items-center zeta-gap-1",
                category === cat
                  ? "zeta-bg-zeta-bg zeta-text-zeta-text zeta-shadow-sm"
                  : "zeta-text-zeta-text-secondary hover:zeta-text-zeta-text"
              )}
            >
              <Filter className="zeta-w-3 zeta-h-3" />
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="zeta-space-y-1">
        {filtered.map((entry) => (
          <div
            key={entry.id}
            className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-overflow-hidden"
          >
            <button
              onClick={() => toggleExpand(entry.id)}
              className="zeta-w-full zeta-px-4 zeta-py-3 zeta-flex zeta-items-center zeta-gap-3 zeta-text-left hover:zeta-bg-zeta-bg-hover zeta-transition-colors"
            >
              {expanded.has(entry.id) ? (
                <ChevronDown className="zeta-w-4 zeta-h-4 zeta-text-zeta-text-tertiary zeta-shrink-0" />
              ) : (
                <ChevronRight className="zeta-w-4 zeta-h-4 zeta-text-zeta-text-tertiary zeta-shrink-0" />
              )}
              <span
                className={cn(
                  "zeta-px-2 zeta-py-0.5 zeta-rounded-full zeta-text-xs zeta-font-medium zeta-shrink-0",
                  CATEGORY_COLORS[entry.category] || "zeta-bg-gray-100 zeta-text-gray-600"
                )}
              >
                {entry.category}
              </span>
              <span className="zeta-text-sm zeta-text-zeta-text zeta-font-medium zeta-flex-1 zeta-truncate">
                {entry.action}
              </span>
              <span className="zeta-text-xs zeta-text-zeta-text-tertiary zeta-truncate zeta-max-w-[140px]">
                {entry.target}
              </span>
              {entry.user && (
                <span className="zeta-text-xs zeta-text-zeta-text-tertiary zeta-flex zeta-items-center zeta-gap-1 zeta-shrink-0">
                  <User className="zeta-w-3 zeta-h-3" />
                  {entry.user}
                </span>
              )}
              <span className="zeta-text-xs zeta-text-zeta-text-tertiary zeta-flex zeta-items-center zeta-gap-1 zeta-shrink-0 zeta-tabular-nums">
                <Clock className="zeta-w-3 zeta-h-3" />
                {formatTime(entry.timestamp)}
              </span>
            </button>
            {expanded.has(entry.id) && (
              <div className="zeta-px-4 zeta-pb-4 zeta-pt-0 zeta-bg-zeta-bg-secondary/30 zeta-border-t zeta-border-zeta-border">
                <div className="zeta-flex zeta-items-center zeta-gap-2 zeta-mb-2 zeta-text-xs zeta-text-zeta-text-tertiary">
                  <GitCompare className="zeta-w-3.5 zeta-h-3.5" />
                  변경 사항
                </div>
                <DiffView before={entry.before} after={entry.after} />
              </div>
            )}
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="zeta-px-6 zeta-py-12 zeta-text-center zeta-text-zeta-text-tertiary zeta-text-sm">
            감사 로그가 없습니다
          </div>
        )}
      </div>
    </div>
  );
}
