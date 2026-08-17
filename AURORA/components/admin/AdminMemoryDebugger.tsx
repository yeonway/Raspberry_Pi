"use client";

import { useState, useEffect } from "react";
import {
  Brain,
  Database,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface MemoryEdge {
  subject: string;
  relation: string;
  object: string;
}

interface MemoryDoc {
  id: string;
  kind: string;
  text: string;
  importance: number;
}

interface MemoryData {
  used: MemoryDoc[];
  unused: MemoryDoc[];
  summary?: string;
  profile?: string;
  preferences?: string;
  relationship?: string;
  events?: string;
  graph?: MemoryEdge[];
}

interface ChatItem {
  id: string;
  title?: string;
  updatedAt?: string;
}

export default function AdminMemoryDebugger() {
  const [chats, setChats] = useState<ChatItem[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<string>("");
  const [memoryData, setMemoryData] = useState<MemoryData | null>(null);
  const [loadingChats, setLoadingChats] = useState(false);
  const [loadingMemory, setLoadingMemory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [expandedSections, setExpandedSections] = useState<
    Record<string, boolean>
  >({
    used: true,
    unused: true,
    metadata: true,
  });

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  useEffect(() => {
    loadChats();
  }, []);

  const loadChats = async () => {
    setLoadingChats(true);
    try {
      const res = await fetch("/api/admin/memory");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "채팅 목록을 불러오지 못했습니다.");
      setChats(data.chats || []);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoadingChats(false);
    }
  };

  const loadMemory = async (chatId: string) => {
    setSelectedChatId(chatId);
    if (!chatId) {
      setMemoryData(null);
      return;
    }
    setLoadingMemory(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/memory?chatId=${encodeURIComponent(chatId)}`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "메모리를 불러오지 못했습니다.");
      setMemoryData(data);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoadingMemory(false);
    }
  };

  const importanceColor = (v: number) => {
    if (v >= 0.8) return "zeta-bg-green-500";
    if (v >= 0.5) return "zeta-bg-yellow-500";
    return "zeta-bg-zeta-muted";
  };

  const renderDoc = (doc: MemoryDoc, index: number) => (
    <div
      key={doc.id || index}
      className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-p-3 zeta-bg-zeta-surface"
    >
      <div className="zeta-flex zeta-items-center zeta-gap-2 zeta-mb-2">
        <span
          className={cn(
            "zeta-px-1.5 zeta-py-0.5 zeta-rounded zeta-text-[10px] zeta-font-medium zeta-text-white",
            doc.kind === "entity"
              ? "zeta-bg-blue-500"
              : doc.kind === "event"
                ? "zeta-bg-purple-500"
                : doc.kind === "scene"
                  ? "zeta-bg-orange-500"
                  : "zeta-bg-zeta-muted"
          )}
        >
          {doc.kind}
        </span>
        <div className="zeta-flex zeta-items-center zeta-gap-1 zeta-text-xs zeta-text-zeta-muted">
          <BarChart3 className="zeta-w-3 zeta-h-3" />
          <div className="zeta-w-16 zeta-h-1.5 zeta-bg-zeta-surface-hover zeta-rounded-full zeta-overflow-hidden">
            <div
              className={cn(
                "zeta-h-full zeta-rounded-full zeta-transition-all",
                importanceColor(doc.importance)
              )}
              style={{ width: `${doc.importance * 100}%` }}
            />
          </div>
          <span>{Math.round(doc.importance * 100)}%</span>
        </div>
      </div>
      <p className="zeta-text-sm zeta-line-clamp-3">{doc.text}</p>
    </div>
  );

  const renderGraphEdges = (edges: MemoryEdge[]) => (
    <div className="zeta-space-y-1.5">
      {edges.map((edge, i) => (
        <div
          key={i}
          className="zeta-flex zeta-items-center zeta-gap-2 zeta-text-xs zeta-p-2 zeta-bg-zeta-surface zeta-rounded-md zeta-border zeta-border-zeta-border"
        >
          <span className="zeta-font-medium zeta-text-zeta-primary">
            {edge.subject}
          </span>
          <span className="zeta-px-1.5 zeta-py-0.5 zeta-rounded zeta-bg-zeta-surface-hover zeta-text-zeta-muted">
            {edge.relation}
          </span>
          <span className="zeta-font-medium zeta-text-zeta-primary">
            {edge.object}
          </span>
        </div>
      ))}
    </div>
  );

  const renderMetadata = () => {
    if (!memoryData) return null;
    const entries = [
      { label: "요약", value: memoryData.summary, icon: Clock, key: "summary" as const },
      { label: "프로필", value: memoryData.profile, icon: Brain, key: "profile" as const },
      {
        label: "선호도",
        value: memoryData.preferences,
        icon: BarChart3,
        key: "preferences" as const,
      },
      {
        label: "관계",
        value: memoryData.relationship,
        icon: Brain,
        key: "relationship" as const,
      },
      { label: "이벤트", value: memoryData.events, icon: Clock, key: "events" as const },
    ].filter((e) => e.value);

    const hasGraph = memoryData.graph && memoryData.graph.length > 0;

    if (entries.length === 0 && !hasGraph) return null;

    return (
      <div className="zeta-space-y-3">
        {entries.map(({ label, value, icon: Icon, key }) => (
          <div key={key}>
            <h5 className="zeta-text-xs zeta-font-medium zeta-text-zeta-muted zeta-mb-1">
              <Icon className="zeta-inline-block zeta-w-3.5 zeta-h-3.5 zeta-mr-1" />
              {label}
            </h5>
            <p className="zeta-text-sm zeta-p-2 zeta-bg-zeta-surface zeta-rounded-md zeta-border zeta-border-zeta-border zeta-whitespace-pre-wrap">
              {value}
            </p>
          </div>
        ))}
        {hasGraph && (
          <div>
            <h5 className="zeta-text-xs zeta-font-medium zeta-text-zeta-muted zeta-mb-1">
              <Brain className="zeta-inline-block zeta-w-3.5 zeta-h-3.5 zeta-mr-1" />
              그래프
            </h5>
            {renderGraphEdges(memoryData.graph!)}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="zeta-space-y-6">
      <div className="zeta-flex zeta-items-center zeta-gap-2">
        <Brain className="zeta-w-5 zeta-h-5 zeta-text-zeta-primary" />
        <h3 className="zeta-text-lg zeta-font-semibold">메모리 디버거</h3>
      </div>

      <div>
        <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1.5">
          <Database className="zeta-inline-block zeta-w-4 zeta-h-4 zeta-mr-1" />
          채팅 선택
        </label>
        {loadingChats ? (
          <p className="zeta-text-sm zeta-text-zeta-muted">불러오는 중...</p>
        ) : (
          <select
            value={selectedChatId}
            onChange={(e) => loadMemory(e.target.value)}
            className="zeta-w-full zeta-max-w-md zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg"
          >
            <option value="">채팅을 선택하세요...</option>
            {chats.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title || c.id} {c.updatedAt ? `(${c.updatedAt})` : ""}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && (
        <div className="zeta-p-3 zeta-bg-red-50 zeta-border zeta-border-red-200 zeta-rounded-md zeta-text-sm zeta-text-red-700">
          {error}
        </div>
      )}

      {loadingMemory && (
        <p className="zeta-text-sm zeta-text-zeta-muted">메모리 불러오는 중...</p>
      )}

      {memoryData && !loadingMemory && (
        <div className="zeta-space-y-4">
          <div className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-overflow-hidden">
            <button
              onClick={() => toggleSection("used")}
              className="zeta-w-full zeta-flex zeta-items-center zeta-gap-2 zeta-p-3 zeta-bg-zeta-surface hover:zeta-bg-zeta-surface-hover zeta-transition-colors"
            >
              {expandedSections.used ? (
                <ChevronDown className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
              ) : (
                <ChevronRight className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
              )}
              <CheckCircle2 className="zeta-w-4 zeta-h-4 zeta-text-green-500" />
              <span className="zeta-text-sm zeta-font-medium">
                사용된 메모리
              </span>
              <span className="zeta-text-xs zeta-text-zeta-muted">
                ({memoryData.used.length})
              </span>
            </button>
            {expandedSections.used && (
              <div className="zeta-p-3 zeta-space-y-2">
                {memoryData.used.length === 0 ? (
                  <p className="zeta-text-sm zeta-text-zeta-muted">
                    사용된 메모리가 없습니다.
                  </p>
                ) : (
                  memoryData.used.map((doc, i) => renderDoc(doc, i))
                )}
              </div>
            )}
          </div>

          <div className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-overflow-hidden">
            <button
              onClick={() => toggleSection("unused")}
              className="zeta-w-full zeta-flex zeta-items-center zeta-gap-2 zeta-p-3 zeta-bg-zeta-surface hover:zeta-bg-zeta-surface-hover zeta-transition-colors"
            >
              {expandedSections.unused ? (
                <ChevronDown className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
              ) : (
                <ChevronRight className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
              )}
              <XCircle className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
              <span className="zeta-text-sm zeta-font-medium">
                관련 미사용 메모리
              </span>
              <span className="zeta-text-xs zeta-text-zeta-muted">
                ({memoryData.unused.length})
              </span>
            </button>
            {expandedSections.unused && (
              <div className="zeta-p-3 zeta-space-y-2">
                {memoryData.unused.length === 0 ? (
                  <p className="zeta-text-sm zeta-text-zeta-muted">
                    미사용 메모리가 없습니다.
                  </p>
                ) : (
                  memoryData.unused.map((doc, i) => renderDoc(doc, i))
                )}
              </div>
            )}
          </div>

          <div className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-overflow-hidden">
            <button
              onClick={() => toggleSection("metadata")}
              className="zeta-w-full zeta-flex zeta-items-center zeta-gap-2 zeta-p-3 zeta-bg-zeta-surface hover:zeta-bg-zeta-surface-hover zeta-transition-colors"
            >
              {expandedSections.metadata ? (
                <ChevronDown className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
              ) : (
                <ChevronRight className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
              )}
              <Database className="zeta-w-4 zeta-h-4 zeta-text-zeta-primary" />
              <span className="zeta-text-sm zeta-font-medium">메타데이터</span>
            </button>
            {expandedSections.metadata && (
              <div className="zeta-p-3">{renderMetadata()}</div>
            )}
          </div>
        </div>
      )}

      {!selectedChatId && !loadingChats && (
        <div className="zeta-text-center zeta-py-8 zeta-text-zeta-muted zeta-text-sm">
          <Database className="zeta-inline-block zeta-w-5 zeta-h-5 zeta-mb-1" />
          <p>채팅을 선택하면 메모리 정보를 확인할 수 있습니다.</p>
        </div>
      )}
    </div>
  );
}
