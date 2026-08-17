"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  BarChart3,
  Clock,
  AlertTriangle,
  Activity,
  Cpu,
  Hash,
  ArrowUpDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

type SubTab = "quality" | "usage" | "modelComparison";
type Period = "today" | "7d" | "30d" | "all";

interface QualityRow {
  characterId: string;
  characterName: string;
  total: number;
  errorRate: number;
  avgOutputLen: number;
  parseErrors: number;
}

interface UsageData {
  requests: number;
  inputTokens: number;
  outputTokens: number;
  failureRate: number;
  byCharacter: Array<{ name: string; requests: number; tokens: number }>;
  byModel: Array<{ name: string; requests: number; tokens: number }>;
}

interface ModelRow {
  model: string;
  requests: number;
  failureRate: number;
  avgTokens: number;
}

type SortKey = keyof ModelRow;

const TABS: { key: SubTab; label: string; icon: typeof BarChart3 }[] = [
  { key: "quality", label: "답변 품질", icon: Activity },
  { key: "usage", label: "사용량", icon: BarChart3 },
  { key: "modelComparison", label: "모델 비교", icon: Cpu },
];

const PERIODS: { key: Period; label: string }[] = [
  { key: "today", label: "오늘" },
  { key: "7d", label: "7일" },
  { key: "30d", label: "30일" },
  { key: "all", label: "전체" },
];

function useFetch<T>(url: string | null): { data: T | null; loading: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!url) return;
    setLoading(true);
    fetch(url)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [url]);

  return { data, loading };
}

function QualityPanel() {
  const { data, loading } = useFetch<{ characters: QualityRow[] }>(
    "/api/admin/stats?section=quality"
  );
  const rows = data?.characters || [];

  if (loading) return <p className="zeta-text-sm zeta-text-zeta-text-tertiary zeta-p-4">로딩 중...</p>;

  return (
    <div className="zeta-overflow-x-auto zeta-border zeta-border-zeta-border zeta-rounded-xl">
      <table className="zeta-w-full zeta-text-sm">
        <thead className="zeta-bg-zeta-bg-secondary zeta-text-zeta-text-secondary">
          <tr>
            <th className="zeta-px-3 zeta-py-2 zeta-text-left zeta-font-medium">캐릭터</th>
            <th className="zeta-px-3 zeta-py-2 zeta-text-right zeta-font-medium">전체 요청</th>
            <th className="zeta-px-3 zeta-py-2 zeta-text-right zeta-font-medium">오류율</th>
            <th className="zeta-px-3 zeta-py-2 zeta-text-right zeta-font-medium">평균 출력 길이</th>
            <th className="zeta-px-3 zeta-py-2 zeta-text-right zeta-font-medium">파싱 오류</th>
          </tr>
        </thead>
        <tbody className="zeta-divide-y zeta-divide-zeta-border">
          {rows.map((r) => (
            <tr key={r.characterId} className="zeta-hover:bg-zeta-bg-hover">
              <td className="zeta-px-3 zeta-py-2 zeta-text-zeta-text zeta-font-medium">
                {r.characterName}
              </td>
              <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-tabular-nums zeta-text-zeta-text-secondary">
                {r.total.toLocaleString()}
              </td>
              <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-tabular-nums">
                <span
                  className={cn(
                    "zeta-inline-block zeta-px-2 zeta-py-0.5 zeta-rounded-full zeta-text-xs zeta-font-medium",
                    r.errorRate > 10
                      ? "zeta-bg-red-100 zeta-text-red-700"
                      : r.errorRate > 5
                      ? "zeta-bg-yellow-100 zeta-text-yellow-700"
                      : "zeta-bg-green-100 zeta-text-green-700"
                  )}
                >
                  {r.errorRate.toFixed(1)}%
                </span>
              </td>
              <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-tabular-nums zeta-text-zeta-text-secondary">
                {r.avgOutputLen.toLocaleString()}
              </td>
              <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-tabular-nums">
                <span
                  className={cn(
                    r.parseErrors > 0
                      ? "zeta-text-red-600 zeta-font-medium"
                      : "zeta-text-zeta-text-tertiary"
                  )}
                >
                  {r.parseErrors}
                </span>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={5} className="zeta-px-6 zeta-py-8 zeta-text-center zeta-text-zeta-text-tertiary">
                데이터가 없습니다
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function UsagePanel() {
  const [period, setPeriod] = useState<Period>("7d");
  const { data, loading } = useFetch<UsageData>(
    `/api/admin/stats?section=usage&period=${period}`
  );

  if (loading) return <p className="zeta-text-sm zeta-text-zeta-text-tertiary zeta-p-4">로딩 중...</p>;
  if (!data) return <p className="zeta-text-sm zeta-text-red-500 zeta-p-4">데이터를 불러올 수 없습니다</p>;

  const maxCharReqs = Math.max(1, ...data.byCharacter.map((c) => c.requests));
  const maxModelReqs = Math.max(1, ...data.byModel.map((m) => m.requests));

  const metrics = [
    { label: "요청 수", value: data.requests.toLocaleString(), icon: Activity },
    { label: "입력 토큰", value: data.inputTokens.toLocaleString(), icon: Hash },
    { label: "출력 토큰", value: data.outputTokens.toLocaleString(), icon: Hash },
    {
      label: "실패율",
      value: `${data.failureRate.toFixed(2)}%`,
      icon: AlertTriangle,
      highlight: data.failureRate > 5,
    },
  ];

  return (
    <div className="zeta-space-y-4">
      <div className="zeta-flex zeta-gap-1 zeta-bg-zeta-bg-secondary zeta-rounded-lg zeta-p-1 zeta-w-fit">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            className={cn(
              "zeta-px-3 zeta-py-1.5 zeta-text-sm zeta-rounded-md zeta-transition-colors",
              period === p.key
                ? "zeta-bg-zeta-bg zeta-text-zeta-text zeta-shadow-sm"
                : "zeta-text-zeta-text-secondary hover:zeta-text-zeta-text"
            )}
          >
            <Clock className="zeta-inline zeta-w-3.5 zeta-h-3.5 zeta-mr-1" />
            {p.label}
          </button>
        ))}
      </div>

      <div className="zeta-grid zeta-grid-cols-2 md:zeta-grid-cols-4 zeta-gap-3">
        {metrics.map((m) => (
          <div
            key={m.label}
            className={cn(
              "zeta-p-4 zeta-rounded-xl zeta-border",
              m.highlight
                ? "zeta-border-red-200 zeta-bg-red-50 dark:zeta-bg-red-950"
                : "zeta-border-zeta-border zeta-bg-zeta-bg-secondary"
            )}
          >
            <div className="zeta-flex zeta-items-center zeta-gap-2 zeta-text-zeta-text-tertiary zeta-text-xs">
              <m.icon className="zeta-w-3.5 zeta-h-3.5" />
              {m.label}
            </div>
            <div className="zeta-mt-1 zeta-text-lg zeta-font-semibold zeta-text-zeta-text zeta-tabular-nums">
              {m.value}
            </div>
          </div>
        ))}
      </div>

      <div className="zeta-grid zeta-grid-cols-1 md:zeta-grid-cols-2 zeta-gap-4">
        <div className="zeta-space-y-2">
          <h4 className="zeta-text-sm zeta-font-medium zeta-text-zeta-text">캐릭터별 요청</h4>
          {data.byCharacter.map((c) => (
            <div key={c.name} className="zeta-flex zeta-items-center zeta-gap-2">
              <span className="zeta-w-20 zeta-text-xs zeta-text-zeta-text-secondary zeta-truncate">
                {c.name}
              </span>
              <div className="zeta-flex-1 zeta-h-4 zeta-bg-zeta-bg-secondary zeta-rounded-full zeta-overflow-hidden">
                <div
                  className="zeta-h-full zeta-bg-blue-500 zeta-rounded-full zeta-transition-all"
                  style={{ width: `${(c.requests / maxCharReqs) * 100}%` }}
                />
              </div>
              <span className="zeta-w-12 zeta-text-xs zeta-text-right zeta-text-zeta-text-tertiary zeta-tabular-nums">
                {c.requests}
              </span>
            </div>
          ))}
        </div>
        <div className="zeta-space-y-2">
          <h4 className="zeta-text-sm zeta-font-medium zeta-text-zeta-text">모델별 요청</h4>
          {data.byModel.map((m) => (
            <div key={m.name} className="zeta-flex zeta-items-center zeta-gap-2">
              <span className="zeta-w-24 zeta-text-xs zeta-text-zeta-text-secondary zeta-truncate zeta-font-mono">
                {m.name}
              </span>
              <div className="zeta-flex-1 zeta-h-4 zeta-bg-zeta-bg-secondary zeta-rounded-full zeta-overflow-hidden">
                <div
                  className="zeta-h-full zeta-bg-purple-500 zeta-rounded-full zeta-transition-all"
                  style={{ width: `${(m.requests / maxModelReqs) * 100}%` }}
                />
              </div>
              <span className="zeta-w-12 zeta-text-xs zeta-text-right zeta-text-zeta-text-tertiary zeta-tabular-nums">
                {m.requests}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ModelComparisonPanel() {
  const { data, loading } = useFetch<{ models: ModelRow[] }>(
    "/api/admin/stats?section=modelComparison"
  );
  const [sortKey, setSortKey] = useState<SortKey>("requests");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const rows = useMemo(() => {
    const list = data?.models || [];
    return [...list].sort((a, b) => {
      const va = a[sortKey] as number;
      const vb = b[sortKey] as number;
      return sortDir === "desc" ? vb - va : va - vb;
    });
  }, [data, sortKey, sortDir]);

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "desc" ? "asc" : "desc"));
      } else {
        setSortKey(key);
        setSortDir("desc");
      }
    },
    [sortKey]
  );

  if (loading) return <p className="zeta-text-sm zeta-text-zeta-text-tertiary zeta-p-4">로딩 중...</p>;

  const TH: React.FC<{ col: SortKey; label: string; align?: string }> = ({
    col,
    label,
    align,
  }) => (
    <th
      onClick={() => handleSort(col)}
      className={cn(
        "zeta-px-3 zeta-py-2 zeta-font-medium zeta-cursor-pointer hover:zeta-bg-zeta-bg-hover zeta-transition-colors zeta-select-none",
        align === "right" ? "zeta-text-right" : "zeta-text-left"
      )}
    >
      <span className="zeta-inline-flex zeta-items-center zeta-gap-1">
        {label}
        <ArrowUpDown
          className={cn(
            "zeta-w-3 zeta-h-3",
            sortKey === col ? "zeta-text-zeta-accent" : "zeta-text-zeta-text-tertiary"
          )}
        />
      </span>
    </th>
  );

  return (
    <div className="zeta-overflow-x-auto zeta-border zeta-border-zeta-border zeta-rounded-xl">
      <table className="zeta-w-full zeta-text-sm">
        <thead className="zeta-bg-zeta-bg-secondary zeta-text-zeta-text-secondary">
          <tr>
            <TH col="model" label="모델" />
            <TH col="requests" label="요청 수" align="right" />
            <TH col="failureRate" label="실패율" align="right" />
            <TH col="avgTokens" label="평균 토큰" align="right" />
          </tr>
        </thead>
        <tbody className="zeta-divide-y zeta-divide-zeta-border">
          {rows.map((r) => (
            <tr key={r.model} className="zeta-hover:bg-zeta-bg-hover">
              <td className="zeta-px-3 zeta-py-2 zeta-text-zeta-text zeta-font-mono zeta-text-xs">
                {r.model}
              </td>
              <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-tabular-nums zeta-text-zeta-text-secondary">
                {r.requests.toLocaleString()}
              </td>
              <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-tabular-nums">
                <span
                  className={cn(
                    "zeta-inline-block zeta-px-2 zeta-py-0.5 zeta-rounded-full zeta-text-xs zeta-font-medium",
                    r.failureRate > 5
                      ? "zeta-bg-red-100 zeta-text-red-700"
                      : r.failureRate > 2
                      ? "zeta-bg-yellow-100 zeta-text-yellow-700"
                      : "zeta-bg-green-100 zeta-text-green-700"
                  )}
                >
                  {r.failureRate.toFixed(1)}%
                </span>
              </td>
              <td className="zeta-px-3 zeta-py-2 zeta-text-right zeta-tabular-nums zeta-text-zeta-text-secondary">
                {r.avgTokens.toLocaleString()}
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="zeta-px-6 zeta-py-8 zeta-text-center zeta-text-zeta-text-tertiary">
                데이터가 없습니다
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminStats() {
  const [tab, setTab] = useState<SubTab>("usage");

  return (
    <div className="zeta-space-y-4">
      <div className="zeta-flex zeta-gap-1 zeta-bg-zeta-bg-secondary zeta-rounded-lg zeta-p-1 zeta-w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "zeta-px-3 zeta-py-1.5 zeta-text-sm zeta-rounded-md zeta-transition-colors zeta-flex zeta-items-center zeta-gap-1.5",
              tab === t.key
                ? "zeta-bg-zeta-bg zeta-text-zeta-text zeta-shadow-sm"
                : "zeta-text-zeta-text-secondary hover:zeta-text-zeta-text"
            )}
          >
            <t.icon className="zeta-w-4 zeta-h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "quality" && <QualityPanel />}
      {tab === "usage" && <UsagePanel />}
      {tab === "modelComparison" && <ModelComparisonPanel />}
    </div>
  );
}
