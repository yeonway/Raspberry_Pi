"use client";

import { useState, useCallback } from "react";
import { FlaskConical, Columns, ThumbsUp, ArrowLeftRight, Save } from "lucide-react";
import { cn } from "@/lib/utils";

interface ABResult {
  config: string;
  response: string;
  model: string;
}

interface SavedABTest {
  id: string;
  prompt: string;
  model: string;
  configA: string;
  configB: string;
  winner: string;
  createdAt: string;
  responseA: string;
  responseB: string;
}

export default function AdminABTest() {
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("");
  const [configA, setConfigA] = useState("");
  const [configB, setConfigB] = useState("");
  const [resultA, setResultA] = useState<ABResult | null>(null);
  const [resultB, setResultB] = useState<ABResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [winner, setWinner] = useState<"A" | "B" | "tie" | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedResults] = useState<SavedABTest[]>([]);

  const handleTest = useCallback(async () => {
    if (!prompt.trim() || !model.trim()) return;

    setLoading(true);
    setWinner(null);

    const fetchConfig = async (config: string): Promise<ABResult> => {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          plot: prompt.trim(),
          config,
        }),
      });

      if (!res.ok) throw new Error("응답 실패");

      if (res.headers.get("content-type")?.includes("text/event-stream")) {
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let content = "";
        let buffer = "";

        if (reader) {
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
                if (typeof delta === "string") content += delta;
              } catch { /* skip */ }
            }
          }
        }

        return { config, response: content, model };
      }

      const data = await res.json();
      return { config, response: data.content ?? data.message ?? JSON.stringify(data), model };
    };

    try {
      const [a, b] = await Promise.all([fetchConfig(configA), fetchConfig(configB)]);
      setResultA(a);
      setResultB(b);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "알 수 없는 오류";
      setResultA({ config: configA, response: `오류: ${msg}`, model });
      setResultB({ config: configB, response: `오류: ${msg}`, model });
    } finally {
      setLoading(false);
    }
  }, [prompt, model, configA, configB]);

  const handleSave = useCallback(async () => {
    if (!winner) return;

    setSaving(true);
    try {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "saveABTest",
          prompt,
          model,
          configA,
          configB,
          winner,
          responseA: resultA?.response ?? "",
          responseB: resultB?.response ?? "",
        }),
      });
    } catch { /* skip */ } finally {
      setSaving(false);
    }
  }, [winner, prompt, model, configA, configB, resultA, resultB]);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
        <label className="block min-w-0">
          <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
            프롬프트
          </span>
          <textarea
            className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text resize-none"
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="테스트할 프롬프트를 입력하세요"
          />
        </label>
        <label className="mt-3 block min-w-0">
          <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
            모델
          </span>
          <select
            className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            <option value="">모델 선택</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4o-mini">GPT-4o Mini</option>
            <option value="claude-3-haiku">Claude 3 Haiku</option>
            <option value="gemini-2-flash">Gemini 2 Flash</option>
          </select>
        </label>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block min-w-0">
            <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
              Config A
            </span>
            <textarea
              className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text resize-none"
              rows={4}
              value={configA}
              onChange={(e) => setConfigA(e.target.value)}
              placeholder='{"temperature": 0.7}'
            />
          </label>
          <label className="block min-w-0">
            <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
              Config B
            </span>
            <textarea
              className="w-full rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2 text-sm text-zeta-text resize-none"
              rows={4}
              value={configB}
              onChange={(e) => setConfigB(e.target.value)}
              placeholder='{"temperature": 1.2}'
            />
          </label>
        </div>

        <button
          className={cn(
            "mt-3 inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition",
            "border-zeta-accent bg-zeta-accentSoft text-zeta-text hover:bg-zeta-panel2",
          )}
          disabled={!prompt.trim() || !model.trim() || loading}
          onClick={handleTest}
          type="button"
        >
          <FlaskConical size={15} />
          {loading ? "테스트 중..." : "양쪽 테스트"}
        </button>
      </div>

      {(resultA || resultB) && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel2 px-2 py-0.5 text-sm font-semibold text-zeta-text">
                <Columns size={14} />A
              </span>
              <span className="text-[11px] text-zeta-soft">{model}</span>
            </div>
            <p className="text-[11px] font-semibold text-zeta-muted sm:text-xs">설정</p>
            <pre className="mt-1 whitespace-pre-wrap break-all text-xs text-zeta-soft bg-zeta-panel2 rounded-lg p-2">
              {resultA?.config ?? configA}
            </pre>
            <p className="mt-2 text-[11px] font-semibold text-zeta-muted sm:text-xs">응답</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-zeta-text">
              {resultA?.response ?? "—"}
            </p>
          </div>

          <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel2 px-2 py-0.5 text-sm font-semibold text-zeta-text">
                <Columns size={14} />B
              </span>
              <span className="text-[11px] text-zeta-soft">{model}</span>
            </div>
            <p className="text-[11px] font-semibold text-zeta-muted sm:text-xs">설정</p>
            <pre className="mt-1 whitespace-pre-wrap break-all text-xs text-zeta-soft bg-zeta-panel2 rounded-lg p-2">
              {resultB?.config ?? configB}
            </pre>
            <p className="mt-2 text-[11px] font-semibold text-zeta-muted sm:text-xs">응답</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-zeta-text">
              {resultB?.response ?? "—"}
            </p>
          </div>
        </div>
      )}

      {resultA && resultB && (
        <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
          <p className="text-[11px] font-semibold text-zeta-muted sm:text-xs">결과 선택</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition",
                winner === "A"
                  ? "border-zeta-accent bg-zeta-accentSoft text-zeta-text"
                  : "border-zeta-line bg-zeta-panel2 text-zeta-muted hover:bg-zeta-panel",
              )}
              onClick={() => setWinner("A")}
              type="button"
            >
              <ThumbsUp size={14} />A 승리
            </button>
            <button
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition",
                winner === "tie"
                  ? "border-zeta-accent bg-zeta-accentSoft text-zeta-text"
                  : "border-zeta-line bg-zeta-panel2 text-zeta-muted hover:bg-zeta-panel",
              )}
              onClick={() => setWinner("tie")}
              type="button"
            >
              <ArrowLeftRight size={14} />무승부
            </button>
            <button
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition",
                winner === "B"
                  ? "border-zeta-accent bg-zeta-accentSoft text-zeta-text"
                  : "border-zeta-line bg-zeta-panel2 text-zeta-muted hover:bg-zeta-panel",
              )}
              onClick={() => setWinner("B")}
              type="button"
            >
              <ThumbsUp size={14} />B 승리
            </button>
            <button
              className="ml-auto inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition border-zeta-line bg-zeta-panel2 text-zeta-muted hover:bg-zeta-panel disabled:cursor-not-allowed disabled:opacity-45"
              disabled={!winner || saving}
              onClick={handleSave}
              type="button"
            >
              <Save size={14} />
              {saving ? "저장 중..." : "저장"}
            </button>
          </div>
        </div>
      )}

      {savedResults.length > 0 && (
        <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
          <p className="text-[11px] font-semibold text-zeta-muted sm:text-xs">이전 결과</p>
          <div className="mt-2 space-y-2">
            {savedResults.map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-zeta-line bg-zeta-panel2 p-2.5 sm:p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel px-2 py-0.5 text-[11px] text-zeta-soft">
                    {item.model}
                  </span>
                  <span className="text-[11px] text-zeta-muted">
                    {new Date(item.createdAt).toLocaleString("ko-KR")}
                  </span>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-lg border px-2 py-0.5 text-[11px] font-semibold",
                      item.winner === "tie"
                        ? "border-zeta-line bg-zeta-panel text-zeta-muted"
                        : "border-zeta-accent bg-zeta-accentSoft text-zeta-text",
                    )}
                  >
                    {item.winner === "A" ? "A 승리" : item.winner === "B" ? "B 승리" : "무승부"}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-zeta-soft">{item.prompt}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
