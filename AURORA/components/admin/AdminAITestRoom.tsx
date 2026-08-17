"use client";

import { useState, useRef, useCallback } from "react";
import { Play, StopCircle, AlertTriangle, Check, Clock, Braces, BookOpen, Brain } from "lucide-react";
import { cn } from "@/lib/utils";

interface TestMessage {
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  metadata?: {
    model?: string;
    tokenCount?: number;
    responseTime?: number;
    parseStatus?: "ok" | "error";
  };
  problemType?: string;
}

const PROBLEM_TYPES = [
  { value: "parsing_error", label: "파싱 오류" },
  { value: "wrong_tone", label: "톤 불일치" },
  { value: "out_of_character", label: "캐릭터 붕괴" },
  { value: "too_short", label: "너무 짧음" },
  { value: "too_long", label: "너무 긺" },
  { value: "irrelevant", label: "무관한 응답" },
  { value: "repetition", label: "반복" },
  { value: "other", label: "기타" },
];

const STORAGE_KEY = "ai-test-room-problems";

function loadProblems(): Record<number, string> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function saveProblems(problems: Record<number, string>) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(problems));
}

export default function AdminAITestRoom() {
  const [character, setCharacter] = useState("");
  const [plot, setPlot] = useState("");
  const [userProfile, setUserProfile] = useState("");
  const [startingScene, setStartingScene] = useState("");
  const [messages, setMessages] = useState<TestMessage[]>([]);
  const [running, setRunning] = useState(false);
  const [problems, setProblems] = useState<Record<number, string>>(loadProblems);
  const [expanded, setExpanded] = useState<number | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleProblemChange = useCallback(
    (messageKey: number, value: string) => {
      const next = { ...problems, [messageKey]: value };
      setProblems(next);
      saveProblems(next);
    },
    [problems],
  );

  const handleStart = useCallback(async () => {
    if (!character.trim() || !plot.trim()) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRunning(true);

    const userMessage: TestMessage = {
      role: "user",
      content: plot.trim(),
      createdAt: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);

    const startTime = performance.now();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character,
          plot: plot.trim(),
          userProfile: userProfile.trim() || undefined,
          startingScene: startingScene.trim() || undefined,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) throw new Error("응답 실패");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assistantContent = "";

      const assistantMessage: TestMessage = {
        role: "assistant",
        content: "",
        createdAt: Date.now(),
        metadata: { parseStatus: "ok" },
      };

      setMessages((prev) => [...prev, assistantMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const data = trimmed.slice(6);
          if (data === "[DONE]") continue;

          try {
            const parsed = JSON.parse(data);
            const delta = parsed?.choices?.[0]?.delta?.content;
            if (typeof delta === "string") {
              assistantContent += delta;
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                if (last?.role === "assistant") {
                  last.content = assistantContent;
                }
                return copy;
              });
            }
          } catch {
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant" && last.metadata) {
                last.metadata.parseStatus = "error";
              }
              return copy;
            });
          }
        }
      }

      const endTime = performance.now();

      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last?.role === "assistant") {
          last.metadata = {
            model: character,
            tokenCount: assistantContent.length,
            responseTime: Math.round(endTime - startTime),
            parseStatus: last.metadata?.parseStatus ?? "ok",
          };
        }
        return copy;
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last?.role === "assistant") {
            last.content = `오류: ${err.message}`;
            if (last.metadata) last.metadata.parseStatus = "error";
          }
          return copy;
        });
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, [character, plot, userProfile, startingScene]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block min-w-0">
            <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
              캐릭터
            </span>
            <select
              className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text"
              value={character}
              onChange={(e) => setCharacter(e.target.value)}
            >
              <option value="">캐릭터 선택</option>
              <option value="aurora">오로라</option>
              <option value="zeta">제타</option>
              <option value="nova">노바</option>
            </select>
          </label>
          <label className="block min-w-0 sm:col-span-1">
            <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
              플롯
            </span>
            <input
              className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text"
              value={plot}
              onChange={(e) => setPlot(e.target.value)}
              placeholder="대화 시작 문장을 입력하세요"
            />
          </label>
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block min-w-0">
            <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
              사용자 프로필
            </span>
            <textarea
              className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text resize-none"
              rows={3}
              value={userProfile}
              onChange={(e) => setUserProfile(e.target.value)}
              placeholder="사용자 프로필 설명"
            />
          </label>
          <label className="block min-w-0">
            <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
              시작 장면
            </span>
            <textarea
              className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text resize-none"
              rows={3}
              value={startingScene}
              onChange={(e) => setStartingScene(e.target.value)}
              placeholder="시작 장면 설명"
            />
          </label>
        </div>
        <div className="mt-3 flex gap-2">
          <button
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition",
              running
                ? "border-zeta-error/40 bg-zeta-errorSoft text-zeta-error"
                : "border-zeta-accent bg-zeta-accentSoft text-zeta-text hover:bg-zeta-panel2",
            )}
            disabled={!character.trim() || !plot.trim()}
            onClick={running ? handleStop : handleStart}
            type="button"
          >
            {running ? <StopCircle size={15} /> : <Play size={15} />}
            {running ? "중지" : "테스트 시작"}
          </button>
        </div>
      </div>

      {messages.length > 0 && (
        <div
          ref={scrollRef}
          className="max-h-[500px] space-y-3 overflow-y-auto rounded-lg border border-zeta-line bg-zeta-panel2 p-3 sm:p-4"
        >
          {messages.map((msg, i) =>
            msg.role === "user" ? (
              <div key={i} className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-2.5 sm:p-3">
                <p className="text-[11px] font-semibold text-blue-400 sm:text-xs">사용자</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-zeta-text">{msg.content}</p>
              </div>
            ) : (
              <div key={i} className="rounded-lg border border-zeta-line bg-zeta-panel p-2.5 sm:p-3">
                <p className="text-[11px] font-semibold text-zeta-soft sm:text-xs">응답</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-zeta-text">{msg.content}</p>

                {msg.metadata && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel2 px-2 py-0.5 text-[11px] text-zeta-soft">
                      <Brain size={12} />
                      {msg.metadata.model ?? "—"}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel2 px-2 py-0.5 text-[11px] text-zeta-soft">
                      <Braces size={12} />
                      {msg.metadata.tokenCount ?? 0}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel2 px-2 py-0.5 text-[11px] text-zeta-soft">
                      <Clock size={12} />
                      {msg.metadata.responseTime ?? 0}ms
                    </span>
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-lg border px-2 py-0.5 text-[11px] font-semibold",
                        msg.metadata.parseStatus === "ok"
                          ? "border-green-500/40 bg-green-500/10 text-green-500"
                          : "border-red-500/40 bg-red-500/10 text-red-500",
                      )}
                    >
                      {msg.metadata.parseStatus === "ok" ? <Check size={12} /> : <AlertTriangle size={12} />}
                      {msg.metadata.parseStatus === "ok" ? "파싱 정상" : "파싱 오류"}
                    </span>
                  </div>
                )}

                <div className="mt-2">
                  <button
                    className="inline-flex items-center gap-1 rounded-lg border border-zeta-line px-2 py-0.5 text-[11px] text-zeta-muted hover:bg-zeta-panel2 transition"
                    onClick={() => setExpanded(expanded === msg.createdAt ? null : msg.createdAt)}
                    type="button"
                  >
                    <BookOpen size={12} />
                    문제 기록
                  </button>
                  {expanded === msg.createdAt && (
                    <select
                      className="mt-1 ml-2 rounded-lg border border-zeta-line bg-zeta-panel2 px-2 py-1 text-[11px] text-zeta-text"
                      value={problems[msg.createdAt] ?? ""}
                      onChange={(e) => handleProblemChange(msg.createdAt, e.target.value)}
                    >
                      <option value="">문제 유형 선택</option>
                      {PROBLEM_TYPES.map((pt) => (
                        <option key={pt.value} value={pt.value}>
                          {pt.label}
                        </option>
                      ))}
                    </select>
                  )}
                  {problems[msg.createdAt] && (
                    <span className="ml-2 inline-flex items-center gap-1 rounded-lg border border-zeta-error/40 bg-zeta-errorSoft px-2 py-0.5 text-[11px] font-semibold text-zeta-error">
                      <AlertTriangle size={12} />
                      {PROBLEM_TYPES.find((p) => p.value === problems[msg.createdAt])?.label}
                    </span>
                  )}
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
