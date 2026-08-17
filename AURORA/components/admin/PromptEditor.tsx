"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Save } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PromptSectionKey } from "@/lib/prompt-store";

type PromptSectionData = {
  key: string;
  label: string;
  content: string;
  isBuiltin: boolean;
  categories: string[];
};

type PromptState = {
  sections: Record<string, string>;
  promptBox: string;
  path: string;
  categoryPath: string;
};

const SECTION_LABELS: Record<string, string> = {
  "response.safe.short": "담백 · 짧게",
  "response.safe.medium": "담백 · 보통",
  "response.safe.long": "담백 · 길게",
  "response.intense.short": "강조 · 짧게",
  "response.intense.medium": "강조 · 보통",
  "response.intense.long": "강조 · 길게",
  "hanAreum.safe": "아름 · 담백",
  "hanAreum.intense": "아름 · 강조",
  "generic.safe": "범용 · 담백",
  "generic.intense": "범용 · 강조",
  "length.short": "길이 · 짧게",
  "length.medium": "길이 · 보통",
  "length.long": "길이 · 길게",
  "shared.rules": "공통 규칙",
};

const RESPONSE_ORDER: PromptSectionKey[] = [
  "response.safe.short",
  "response.safe.medium",
  "response.safe.long",
  "response.intense.short",
  "response.intense.medium",
  "response.intense.long",
];

const PERSONA_ORDER: PromptSectionKey[] = [
  "hanAreum.safe",
  "hanAreum.intense",
  "generic.safe",
  "generic.intense",
];

const UTILITY_ORDER: PromptSectionKey[] = [
  "length.short",
  "length.medium",
  "length.long",
  "shared.rules",
];

export function PromptEditor() {
  const [state, setState] = useState<PromptState | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeView, setActiveView] = useState<"cards" | "raw">("cards");
  const [rawDraft, setRawDraft] = useState("");

  const load = async () => {
    setIsLoading(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/admin/prompts");
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "불러오기 실패");
      setState(data);
      setDrafts(data.sections ?? {});
      setRawDraft(data.promptBox ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "불러오기 실패");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line

  const saveSection = async (key: string, value: string) => {
    setIsSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/admin/prompts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ sections: { [key]: value } }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "저장 실패");
      setState(data);
      setDrafts(data.sections ?? {});
      setNotice("저장됨");
      setTimeout(() => setNotice(""), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setIsSaving(false);
    }
  };

  const saveRaw = async () => {
    setIsSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/admin/prompts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ promptBox: rawDraft }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "저장 실패");
      setState(data);
      setDrafts(data.sections ?? {});
      setNotice("저장됨");
      setTimeout(() => setNotice(""), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setIsSaving(false);
    }
  };

  const getDisplaySections = (): PromptSectionData[] => {
    const all: PromptSectionData[] = [];
    for (const key of [...RESPONSE_ORDER, ...PERSONA_ORDER, ...UTILITY_ORDER]) {
      all.push({
        key,
        label: SECTION_LABELS[key] ?? key,
        content: drafts[key] ?? state?.sections[key] ?? "",
        isBuiltin: RESPONSE_ORDER.includes(key),
        categories: [],
      });
    }
    return all;
  };

  return (
    <section className="min-w-0 rounded-lg border border-zeta-line bg-zeta-panel p-4">
      <div className="mb-4 flex flex-col gap-3 border-b border-zeta-line pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold sm:text-lg">프롬프트 편집</h2>
          <p className="mt-1 text-xs text-zeta-muted">
            {state?.path ?? "..."}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className={cn(
              "h-9 rounded-lg px-3 text-xs font-semibold transition",
              activeView === "cards"
                ? "bg-zeta-accent text-zeta-buttonText"
                : "border border-zeta-line text-zeta-muted hover:bg-zeta-panel2",
            )}
            onClick={() => setActiveView("cards")}
            type="button"
          >
            카드 보기
          </button>
          <button
            className={cn(
              "h-9 rounded-lg px-3 text-xs font-semibold transition",
              activeView === "raw"
                ? "bg-zeta-accent text-zeta-buttonText"
                : "border border-zeta-line text-zeta-muted hover:bg-zeta-panel2",
            )}
            onClick={() => setActiveView("raw")}
            type="button"
          >
            원문 보기
          </button>
          <button
            aria-label="새로고침"
            className="inline-flex size-9 items-center justify-center rounded-lg border border-zeta-line text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            disabled={isLoading}
            onClick={load}
            title="새로고침"
            type="button"
          >
            <RefreshCw size={15} className={isLoading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {error ? (
        <p className="mb-4 rounded-lg border border-zeta-error/40 bg-zeta-errorSoft px-3 py-2 text-sm text-zeta-error">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="mb-4 rounded-lg border border-zeta-success/40 bg-zeta-successSoft px-3 py-2 text-sm text-zeta-success">
          {notice}
        </p>
      ) : null}

      {activeView === "cards" ? (
        <div className="space-y-4">
          <SectionGroup
            title="응답 스타일 조합"
            description="safe/intense × short/medium/long 조합"
            sections={getDisplaySections().filter((s) => s.isBuiltin)}
            onSave={saveSection}
            onDraftChange={setDrafts}
          />
          <SectionGroup
            title="페르소나"
            description="캐릭터별 말투 프리셋 (레거시)"
            sections={getDisplaySections().filter(
              (s) => PERSONA_ORDER.includes(s.key as PromptSectionKey),
            )}
            onSave={saveSection}
            onDraftChange={setDrafts}
          />
          <SectionGroup
            title="길이 & 공통 규칙"
            description="응답 길이 계약과 공통 포맷 규칙"
            sections={getDisplaySections().filter(
              (s) => UTILITY_ORDER.includes(s.key as PromptSectionKey),
            )}
            onSave={saveSection}
            onDraftChange={setDrafts}
          />
        </div>
      ) : (
        <div className="space-y-3">
          <textarea
            className="textarea min-h-[60vh] font-mono text-xs leading-relaxed"
            onChange={(e) => setRawDraft(e.target.value)}
            value={rawDraft}
          />
          <div className="flex justify-end">
            <button
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-zeta-accent px-4 text-sm font-semibold text-zeta-buttonText transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isSaving}
              onClick={saveRaw}
              type="button"
            >
              <Save size={15} />
              {isSaving ? "저장 중..." : "원문 저장"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function SectionGroup({
  title,
  description,
  sections,
  onSave,
  onDraftChange,
}: {
  title: string;
  description: string;
  sections: PromptSectionData[];
  onSave: (key: string, value: string) => void;
  onDraftChange: React.Dispatch<React.SetStateAction<Record<string, string>>>;
}) {
  if (!sections.length) return null;

  return (
    <div>
      <div className="mb-2">
        <h3 className="text-sm font-semibold text-zeta-text">{title}</h3>
        <p className="text-[11px] text-zeta-soft">{description}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {sections.map((section) => (
          <div
            className="overflow-hidden rounded-lg border border-zeta-line bg-zeta-panel2"
            key={section.key}
          >
            <div className="flex items-center justify-between gap-2 border-b border-zeta-line/50 px-3 py-2">
              <span className="text-xs font-semibold text-zeta-text">
                {section.label}
              </span>
              <code className="truncate text-[10px] text-zeta-soft">
                {section.key}
              </code>
            </div>
            <textarea
              className="min-h-28 w-full resize-y bg-transparent px-3 py-2 text-sm leading-relaxed text-zeta-text outline-none placeholder:text-zeta-soft"
              onChange={(e) => {
                onDraftChange((prev) => ({ ...prev, [section.key]: e.target.value }));
              }}
              onBlur={(e) => {
                if (e.target.value !== sections.find((s) => s.key === section.key)?.content) {
                  onSave(section.key, e.target.value);
                }
              }}
              value={section.content}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
