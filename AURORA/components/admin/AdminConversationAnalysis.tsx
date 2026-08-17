"use client";

import { useState, useMemo, useCallback } from "react";
import {
  MessageCircle,
  AlertTriangle,
  ExternalLink,
  CheckCircle2,
  Brain,
  User,
  ChevronDown,
  ChevronRight,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatLogEntry, Character } from "@/types/chat";

type Status = "신규" | "확인 중" | "해결됨" | "무시";

interface ConversationRow {
  id: string;
  characterName: string;
  characterId: string;
  userName: string;
  model: string;
  tokens: number;
  parseStatus: "ok" | "error";
  messages: Array<{ role: string; content: string }>;
  status: Status;
}

interface Props {
  logs: ChatLogEntry[];
  characters: Character[];
}

const STATUS_OPTIONS: Status[] = ["신규", "확인 중", "해결됨", "무시"];
const STORAGE_KEY = "adminConversationStatuses";

function loadStatuses(): Record<string, Status> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveStatuses(statuses: Record<string, Status>) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(statuses));
}

export default function AdminConversationAnalysis({ logs, characters }: Props) {
  const [filter, setFilter] = useState<"all" | "errors">("all");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [statuses, setStatuses] = useState<Record<string, Status>>(loadStatuses);

  const rows = useMemo<ConversationRow[]>(() => {
    return logs.map((log, idx) => {
      const char = characters.find((c) => c.id === log.characterId);
      return {
        id: log.id || `log-${idx}`,
        characterName: char?.name || log.characterId || "—",
        characterId: log.characterId || "",
        userName: log.userName || "—",
        model: log.usedModel?.model || log.requestedModel?.model || "—",
        tokens: log.assistantContent?.length ?? 0,
        parseStatus: log.error ? "error" : "ok",
        messages: log.messages || [],
        status: "신규",
      };
    });
  }, [logs, characters]);

  const filtered = useMemo(() => {
    let result = rows.map((r) => ({ ...r, status: statuses[r.id] || "신규" }));
    if (filter === "errors") result = result.filter((r) => r.parseStatus === "error");
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (r) =>
          r.characterName.toLowerCase().includes(q) ||
          r.userName.toLowerCase().includes(q)
      );
    }
    return result;
  }, [rows, filter, search, statuses]);

  const toggleExpand = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  }, []);

  const setStatus = useCallback(
    (id: string, status: Status) => {
      setStatuses((prev) => {
        const next = { ...prev, [id]: status };
        saveStatuses(next);
        return next;
      });
    },
    []
  );

  const openTestRoom = useCallback(
    (row: ConversationRow) => {
      if (typeof window === "undefined") return;
      const state = {
        characterId: row.characterId,
        characterName: row.characterName,
        userName: row.userName,
        messages: row.messages,
        model: row.model,
      };
      sessionStorage.setItem("aiTestRoomState", JSON.stringify(state));
      window.open("/admin/test-room", "_blank");
    },
    []
  );

  const statusBadge = (s: Status) => {
    const map: Record<Status, string> = {
      신규: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
      "확인 중": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
      해결됨: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      무시: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
    };
    return map[s];
  };

  return (
    <div className="zeta-space-y-4">
      <div className="zeta-flex zeta-items-center zeta-gap-3 zeta-flex-wrap">
        <div className="zeta-flex zeta-gap-1 zeta-bg-zeta-bg-secondary zeta-rounded-lg zeta-p-1">
          <button
            onClick={() => setFilter("all")}
            className={cn(
              "zeta-px-3 zeta-py-1.5 zeta-text-sm zeta-rounded-md zeta-transition-colors",
              filter === "all"
                ? "zeta-bg-zeta-bg zeta-text-zeta-text zeta-shadow-sm"
                : "zeta-text-zeta-text-secondary hover:zeta-text-zeta-text"
            )}
          >
            <MessageCircle className="zeta-inline zeta-w-4 zeta-h-4 zeta-mr-1" />
            전체
          </button>
          <button
            onClick={() => setFilter("errors")}
            className={cn(
              "zeta-px-3 zeta-py-1.5 zeta-text-sm zeta-rounded-md zeta-transition-colors",
              filter === "errors"
                ? "zeta-bg-zeta-bg zeta-text-zeta-text zeta-shadow-sm"
                : "zeta-text-zeta-text-secondary hover:zeta-text-zeta-text"
            )}
          >
            <AlertTriangle className="zeta-inline zeta-w-4 zeta-h-4 zeta-mr-1" />
            오류만
          </button>
        </div>
        <div className="zeta-relative zeta-flex-1 zeta-min-w-[200px]">
          <Search className="zeta-absolute zeta-left-3 zeta-top-1/2 zeta--translate-y-1/2 zeta-w-4 zeta-h-4 zeta-text-zeta-text-tertiary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="캐릭터 또는 유저 검색..."
            className="zeta-w-full zeta-pl-9 zeta-pr-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg-secondary zeta-border zeta-border-zeta-border zeta-rounded-lg focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent zeta-text-zeta-text"
          />
        </div>
      </div>

      <div className="zeta-overflow-x-auto zeta-border zeta-border-zeta-border zeta-rounded-xl">
        <table className="zeta-w-full zeta-text-sm">
          <thead className="zeta-bg-zeta-bg-secondary zeta-text-zeta-text-secondary">
            <tr>
              <th className="zeta-px-3 zeta-py-2 zeta-text-left zeta-font-medium">캐릭터</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-left zeta-font-medium">사용자</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-left zeta-font-medium">모델</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-right zeta-font-medium">토큰</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-center zeta-font-medium">파싱</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-center zeta-font-medium">상태</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-center zeta-font-medium">작업</th>
            </tr>
          </thead>
          <tbody className="zeta-divide-y zeta-divide-zeta-border">
            {filtered.map((row) => (
              <>
                <tr
                  key={row.id}
                  className="zeta-hover:bg-zeta-bg-hover zeta-transition-colors"
                >
                  <td className="zeta-px-3 zeta-py-2 zeta-flex zeta-items-center zeta-gap-2">
                    <button
                      onClick={() => toggleExpand(row.id)}
                      className="zeta-text-zeta-text-tertiary hover:zeta-text-zeta-text"
                    >
                      {expanded.has(row.id) ? (
                        <ChevronDown className="zeta-w-4 zeta-h-4" />
                      ) : (
                        <ChevronRight className="zeta-w-4 zeta-h-4" />
                      )}
                    </button>
                    <Brain className="zeta-w-4 zeta-h-4 zeta-text-zeta-accent" />
                    <span className="zeta-text-zeta-text">{row.characterName}</span>
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-zeta-text">
                    <User className="zeta-inline zeta-w-3.5 zeta-h-3.5 zeta-mr-1 zeta-text-zeta-text-tertiary" />
                    {row.userName}
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-zeta-text-secondary zeta-text-xs zeta-font-mono">
                    {row.model}
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-text-zeta-text-secondary zeta-tabular-nums">
                    {row.tokens.toLocaleString()}
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-center">
                    {row.parseStatus === "ok" ? (
                      <CheckCircle2 className="zeta-inline zeta-w-4 zeta-h-4 zeta-text-green-500" />
                    ) : (
                      <AlertTriangle className="zeta-inline zeta-w-4 zeta-h-4 zeta-text-red-500" />
                    )}
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-center">
                    <select
                      value={statuses[row.id] || "신규"}
                      onChange={(e) => setStatus(row.id, e.target.value as Status)}
                      className={cn(
                        "zeta-text-xs zeta-px-2 zeta-py-1 zeta-rounded-full zeta-border-0 zeta-cursor-pointer zeta-appearance-none",
                        statusBadge(statuses[row.id] || "신규")
                      )}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-center">
                    <button
                      onClick={() => openTestRoom(row)}
                      className="zeta-inline-flex zeta-items-center zeta-gap-1 zeta-text-xs zeta-px-2 zeta-py-1 zeta-bg-zeta-accent zeta-text-white zeta-rounded-md hover:zeta-bg-zeta-accent-hover zeta-transition-colors"
                    >
                      <ExternalLink className="zeta-w-3.5 zeta-h-3.5" />
                      테스트실에서 열기
                    </button>
                  </td>
                </tr>
                {expanded.has(row.id) && (
                  <tr key={`${row.id}-expanded`}>
                    <td colSpan={7} className="zeta-px-6 zeta-py-3 zeta-bg-zeta-bg-secondary/50">
                      <div className="zeta-space-y-2 zeta-max-h-80 zeta-overflow-y-auto">
                        {row.messages.map((msg, i) => (
                          <div
                            key={i}
                            className={cn(
                              "zeta-p-3 zeta-rounded-lg zeta-text-sm",
                              msg.role === "assistant"
                                ? "zeta-bg-blue-50 dark:zeta-bg-blue-950 zeta-ml-4"
                                : msg.role === "user"
                                ? "zeta-bg-zeta-bg zeta-mr-4 zeta-border zeta-border-zeta-border"
                                : "zeta-bg-gray-50 dark:zeta-bg-gray-900"
                            )}
                          >
                            <span className="zeta-text-xs zeta-font-medium zeta-text-zeta-text-tertiary zeta-uppercase">
                              {msg.role}
                            </span>
                            <p className="zeta-mt-1 zeta-whitespace-pre-wrap zeta-text-zeta-text">
                              {typeof msg.content === "string"
                                ? msg.content
                                : JSON.stringify(msg.content)}
                            </p>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="zeta-px-6 zeta-py-8 zeta-text-center zeta-text-zeta-text-tertiary">
                  표시할 대화가 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
