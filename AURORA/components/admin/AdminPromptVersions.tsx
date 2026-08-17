"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { GitBranch, History, RotateCcw, Diff, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface PromptSection {
  key: string;
  label: string;
  current: string;
}

interface PromptVersion {
  id: string;
  date: string;
  content: string;
}

const STORAGE_KEY = "admin-prompt-versions";

function loadVersions(): Record<string, PromptVersion[]> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function saveVersions(versions: Record<string, PromptVersion[]>) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(versions));
}

function computeDiff(oldText: string, newText: string) {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");

  const result: { type: "added" | "removed"; text: string }[] = [];
  const maxLen = Math.max(oldLines.length, newLines.length);

  for (let i = 0; i < maxLen; i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];
    if (oldLine === undefined && newLine !== undefined) {
      result.push({ type: "added", text: newLine });
    } else if (newLine === undefined && oldLine !== undefined) {
      result.push({ type: "removed", text: oldLine });
    } else if (oldLine !== newLine) {
      if (oldLine) result.push({ type: "removed", text: oldLine });
      if (newLine) result.push({ type: "added", text: newLine });
    }
  }

  return result;
}

export default function AdminPromptVersions() {
  const [sections, setSections] = useState<PromptSection[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [versions, setVersions] = useState<Record<string, PromptVersion[]>>(loadVersions);
  const [diffView, setDiffView] = useState<{ oldIdx: number; newIdx: number } | null>(null);
  const [diffLines, setDiffLines] = useState<{ type: "added" | "removed"; text: string }[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/admin/prompts")
      .then((res) => res.json())
      .then((data) => {
        const list = Array.isArray(data) ? data : data.sections ?? [];
        setSections(list);
        if (list.length > 0) {
          setSelectedKey((prev) => prev || list[0].key);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    saveVersions(versions);
  }, [versions]);

  const currentSection = sections.find((s) => s.key === selectedKey);
  const sectionVersions = useMemo(() => versions[selectedKey] ?? [], [versions, selectedKey]);

  const handleSaveVersion = useCallback(() => {
    if (!selectedKey || !currentSection) return;

    const newVersion: PromptVersion = {
      id: crypto.randomUUID?.() ?? `${Date.now()}`,
      date: new Date().toISOString(),
      content: currentSection.current,
    };

    setVersions((prev) => ({
      ...prev,
      [selectedKey]: [newVersion, ...(prev[selectedKey] ?? [])],
    }));
  }, [selectedKey, currentSection]);

  const handleRestore = useCallback(
    async (version: PromptVersion) => {
      setLoading(true);
      try {
        await fetch("/api/admin/prompts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: selectedKey, content: version.content }),
        });

        setSections((prev) =>
          prev.map((s) => (s.key === selectedKey ? { ...s, current: version.content } : s)),
        );
      } catch { /* skip */ } finally {
        setLoading(false);
      }
    },
    [selectedKey],
  );

  const handleShowDiff = useCallback(
    (versionIdx: number) => {
      if (!currentSection) return;

      const oldContent = versionIdx < sectionVersions.length - 1
        ? sectionVersions[versionIdx + 1]?.content ?? ""
        : "";

      const newContent = sectionVersions[versionIdx]?.content ?? "";
      setDiffLines(computeDiff(oldContent, newContent));
      setDiffView({ oldIdx: versionIdx + 1, newIdx: versionIdx });
    },
    [currentSection, sectionVersions],
  );

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
        <div className="flex flex-wrap items-center gap-2">
          <GitBranch size={16} className="text-zeta-soft" />
          {sections.map((section) => (
            <button
              key={section.key}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-xs font-semibold transition",
                selectedKey === section.key
                  ? "border-zeta-accent bg-zeta-accentSoft text-zeta-text"
                  : "border-zeta-line bg-zeta-panel2 text-zeta-muted hover:bg-zeta-panel",
              )}
              onClick={() => {
                setSelectedKey(section.key);
                setDiffView(null);
              }}
              type="button"
            >
              {section.label ?? section.key}
            </button>
          ))}
        </div>
      </div>

      {currentSection && (
        <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-zeta-text">
              {currentSection.label ?? currentSection.key}
            </p>
            <button
              className="inline-flex items-center gap-1.5 rounded-lg border border-zeta-line px-3 py-1.5 text-xs font-semibold text-zeta-muted hover:bg-zeta-panel2 transition"
              onClick={handleSaveVersion}
              type="button"
            >
              <History size={14} />
              버전 저장
            </button>
          </div>
          <pre className="mt-2 max-h-32 overflow-y-auto whitespace-pre-wrap break-all rounded-lg border border-zeta-line bg-zeta-panel2 p-2.5 text-xs text-zeta-text">
            {currentSection.current}
          </pre>
        </div>
      )}

      {sectionVersions.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-semibold text-zeta-muted sm:text-xs flex items-center gap-1.5">
            <History size={14} />
            버전 기록 ({sectionVersions.length})
          </p>
          {sectionVersions.map((version, idx) => (
            <div
              key={version.id}
              className="rounded-lg border border-zeta-line bg-zeta-panel2 p-2.5 sm:p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel px-2 py-0.5 text-[11px] text-zeta-soft">
                  <Clock size={12} />
                  {new Date(version.date).toLocaleString("ko-KR")}
                </span>
                <div className="flex gap-1.5">
                  <button
                    className="inline-flex items-center gap-1 rounded-lg border border-zeta-line px-2 py-0.5 text-[11px] text-zeta-muted hover:bg-zeta-panel transition"
                    onClick={() => handleShowDiff(idx)}
                    type="button"
                  >
                    <Diff size={12} />
                    비교
                  </button>
                  <button
                    className="inline-flex items-center gap-1 rounded-lg border border-zeta-line px-2 py-0.5 text-[11px] text-zeta-muted hover:bg-zeta-panel transition"
                    disabled={loading}
                    onClick={() => handleRestore(version)}
                    type="button"
                  >
                    <RotateCcw size={12} />
                    {loading ? "복원 중..." : "복원"}
                  </button>
                </div>
              </div>
              <p className="mt-1.5 line-clamp-2 text-xs text-zeta-soft">
                {version.content.slice(0, 50)}
                {version.content.length > 50 ? "..." : ""}
              </p>
            </div>
          ))}
        </div>
      )}

      {diffView && diffLines.length > 0 && (
        <div className="rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
          <p className="text-[11px] font-semibold text-zeta-muted sm:text-xs flex items-center gap-1.5">
            <Diff size={14} />
            버전 비교
          </p>
          <div className="mt-2 max-h-80 overflow-y-auto rounded-lg border border-zeta-line bg-zeta-panel2 p-2.5">
            {diffLines.map((line, i) => (
              <div
                key={i}
                className={cn(
                  "whitespace-pre-wrap break-all px-2 py-0.5 text-xs font-mono",
                  line.type === "added"
                    ? "bg-green-500/10 text-green-400"
                    : "bg-red-500/10 text-red-400",
                )}
              >
                <span className="mr-2 font-semibold">{line.type === "added" ? "+" : "-"}</span>
                {line.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedKey && sectionVersions.length === 0 && (
        <p className="text-xs text-zeta-muted text-center py-4">
          저장된 버전이 없습니다
        </p>
      )}
    </div>
  );
}
