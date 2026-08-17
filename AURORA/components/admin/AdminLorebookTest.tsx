"use client";

import { useState, useCallback } from "react";
import { Search, BookOpen, AlertTriangle, Hash } from "lucide-react";
import { cn } from "@/lib/utils";

interface LorebookResult {
  entryName: string;
  matchedKeywords: string[];
  matchCount: number;
  overload?: boolean;
  duplicate?: boolean;
}

interface LorebookWarning {
  type: "overload" | "duplicate";
  message: string;
  entries: string[];
}

interface LorebookTestResponse {
  results: LorebookResult[];
  warnings: LorebookWarning[];
}

function getMatchColor(count: number) {
  if (count >= 5) return "text-red-400";
  if (count >= 3) return "text-yellow-400";
  if (count >= 1) return "text-green-400";
  return "text-zeta-muted";
}

export default function AdminLorebookTest() {
  const [text, setText] = useState("");
  const [results, setResults] = useState<LorebookResult[]>([]);
  const [warnings, setWarnings] = useState<LorebookWarning[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTest = useCallback(async () => {
    if (!text.trim()) return;

    setLoading(true);
    setError("");
    setResults([]);
    setWarnings([]);

    try {
      const res = await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "testLorebooks", text: text.trim() }),
      });

      if (!res.ok) throw new Error("로어북 테스트 실패");

      const data: LorebookTestResponse = await res.json();
      setResults(data.results ?? []);
      setWarnings(data.warnings ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류");
    } finally {
      setLoading(false);
    }
  }, [text]);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
        <label className="block min-w-0">
          <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
            <BookOpen size={13} className="inline mr-1" />
            테스트 문장
          </span>
          <textarea
            className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text resize-none"
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="로어북을 테스트할 문장을 입력하세요"
          />
        </label>
        <button
          className={cn(
            "mt-3 inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition",
            "border-zeta-accent bg-zeta-accentSoft text-zeta-text hover:bg-zeta-panel2",
          )}
          disabled={!text.trim() || loading}
          onClick={handleTest}
          type="button"
        >
          <Search size={15} />
          {loading ? "테스트 중..." : "테스트"}
        </button>
        {error && (
          <p className="mt-2 text-xs text-zeta-error flex items-center gap-1">
            <AlertTriangle size={13} />
            {error}
          </p>
        )}
      </div>

      {warnings.length > 0 && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 sm:p-4">
          <p className="text-[11px] font-semibold text-yellow-400 sm:text-xs flex items-center gap-1.5">
            <AlertTriangle size={14} />
            경고
          </p>
          <ul className="mt-2 space-y-1.5">
            {warnings.map((w, i) => (
              <li
                key={i}
                className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-2 text-xs text-yellow-300"
              >
                <p className="font-semibold">
                  {w.type === "overload" ? "오버로드" : "중복"}
                </p>
                <p className="mt-0.5 text-yellow-400/80">{w.message}</p>
                {w.entries.length > 0 && (
                  <p className="mt-0.5 text-[11px] text-yellow-400/50">
                    항목: {w.entries.join(", ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-semibold text-zeta-muted sm:text-xs flex items-center gap-1.5">
            <BookOpen size={14} />
            매칭 결과 ({results.length})
          </p>
          {results.map((result, i) => (
            <div
              key={i}
              className="rounded-lg border border-zeta-line bg-zeta-panel2 p-2.5 sm:p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-semibold text-zeta-text">
                  {result.entryName}
                </span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-lg border px-2 py-0.5 text-[11px] font-semibold",
                    result.matchCount >= 5
                      ? "border-red-500/30 bg-red-500/10 text-red-400"
                      : result.matchCount >= 3
                        ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                        : "border-green-500/30 bg-green-500/10 text-green-400",
                  )}
                >
                  <Hash size={12} />
                  {result.matchCount} 매치
                </span>
              </div>
              {result.matchedKeywords.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {result.matchedKeywords.map((kw) => (
                    <span
                      key={kw}
                      className={cn(
                        "rounded-md border border-zeta-line bg-zeta-panel px-1.5 py-0.5 text-[11px]",
                        getMatchColor(result.matchCount),
                      )}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              )}
              {(result.overload || result.duplicate) && (
                <p className="mt-1.5 text-[11px] text-zeta-error flex items-center gap-1">
                  <AlertTriangle size={12} />
                  {result.overload ? "오버로드" : ""}
                  {result.overload && result.duplicate ? " · " : ""}
                  {result.duplicate ? "중복" : ""}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && warnings.length === 0 && !loading && !error && text.trim() && (
        <p className="text-xs text-zeta-muted text-center py-4">
          결과가 없습니다
        </p>
      )}
    </div>
  );
}
