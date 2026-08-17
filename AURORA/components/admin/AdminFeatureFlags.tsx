"use client";

import { useState, useEffect, useCallback } from "react";
import { Flag, Shield, Users, Globe, Plus, Save, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

type FlagStatus = "off" | "admin" | "all";

interface FeatureFlag {
  key: string;
  label: string;
  description: string;
  status: FlagStatus;
}

const STATUS_MAP: Record<FlagStatus, { label: string; className: string }> = {
  off: { label: "비활성", className: "zeta-bg-red-100 zeta-text-red-700 dark:zeta-bg-red-900 dark:zeta-text-red-200" },
  admin: { label: "관리자", className: "zeta-bg-yellow-100 zeta-text-yellow-700 dark:zeta-bg-yellow-900 dark:zeta-text-yellow-200" },
  all: { label: "전체", className: "zeta-bg-green-100 zeta-text-green-700 dark:zeta-bg-green-900 dark:zeta-text-green-200" },
};

const STATUS_OPTIONS: { value: FlagStatus; label: string; icon: typeof Shield }[] = [
  { value: "off", label: "비활성", icon: Shield },
  { value: "admin", label: "관리자 전용", icon: Shield },
  { value: "all", label: "전체 공개", icon: Globe },
];

const ICON_MAP: Record<FlagStatus, typeof Shield> = {
  off: Shield,
  admin: Users,
  all: Globe,
};

function useFeatures() {
  const [features, setFeatures] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchFeatures = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/config");
      const data = await res.json();
      setFeatures(data.features || []);
    } catch {
      setFeatures([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeatures();
  }, [fetchFeatures]);

  const saveFeatures = useCallback(
    async (updated: FeatureFlag[]) => {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "saveFeatures", features: updated }),
      });
      setFeatures(updated);
    },
    []
  );

  return { features, loading, saveFeatures, refetch: fetchFeatures };
}

export default function AdminFeatureFlags() {
  const { features, loading, saveFeatures } = useFeatures();
  const [showAdd, setShowAdd] = useState(false);
  const [newFlag, setNewFlag] = useState({ key: "", label: "", description: "", status: "off" as FlagStatus });
  const [editStatuses, setEditStatuses] = useState<Record<string, FlagStatus>>({});

  const handleStatusChange = useCallback(
    (key: string, status: FlagStatus) => {
      setEditStatuses((prev) => ({ ...prev, [key]: status }));
      const updated = features.map((f) => (f.key === key ? { ...f, status } : f));
      saveFeatures(updated);
    },
    [features, saveFeatures]
  );

  const handleDelete = useCallback(
    (key: string) => {
      const updated = features.filter((f) => f.key !== key);
      saveFeatures(updated);
    },
    [features, saveFeatures]
  );

  const handleAdd = useCallback(() => {
    if (!newFlag.key.trim() || !newFlag.label.trim()) return;
    const updated = [
      ...features,
      {
        key: newFlag.key.trim(),
        label: newFlag.label.trim(),
        description: newFlag.description.trim(),
        status: newFlag.status,
      },
    ];
    saveFeatures(updated);
    setNewFlag({ key: "", label: "", description: "", status: "off" });
    setShowAdd(false);
  }, [features, newFlag, saveFeatures]);

  if (loading) return <p className="zeta-text-sm zeta-text-zeta-text-tertiary zeta-p-4">로딩 중...</p>;

  return (
    <div className="zeta-space-y-4">
      <div className="zeta-flex zeta-items-center zeta-justify-between">
        <h3 className="zeta-text-sm zeta-font-medium zeta-text-zeta-text-secondary zeta-flex zeta-items-center zeta-gap-2">
          <Flag className="zeta-w-4 zeta-h-4" />
          기능 플래그 ({features.length})
        </h3>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="zeta-inline-flex zeta-items-center zeta-gap-1.5 zeta-px-3 zeta-py-1.5 zeta-text-sm zeta-bg-zeta-accent zeta-text-white zeta-rounded-lg hover:zeta-bg-zeta-accent-hover zeta-transition-colors"
        >
          <Plus className="zeta-w-4 zeta-h-4" />
          추가
        </button>
      </div>

      {showAdd && (
        <div className="zeta-p-4 zeta-border zeta-border-zeta-border zeta-rounded-xl zeta-bg-zeta-bg-secondary zeta-space-y-3">
          <div className="zeta-grid zeta-grid-cols-1 md:zeta-grid-cols-2 zeta-gap-3">
            <input
              type="text"
              value={newFlag.key}
              onChange={(e) => setNewFlag((p) => ({ ...p, key: e.target.value }))}
              placeholder="키 (예: feature.newUI)"
              className="zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
            />
            <input
              type="text"
              value={newFlag.label}
              onChange={(e) => setNewFlag((p) => ({ ...p, label: e.target.value }))}
              placeholder="레이블 (예: 새 UI)"
              className="zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
            />
          </div>
          <input
            type="text"
            value={newFlag.description}
            onChange={(e) => setNewFlag((p) => ({ ...p, description: e.target.value }))}
            placeholder="설명"
            className="zeta-w-full zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
          />
          <div className="zeta-flex zeta-items-center zeta-gap-3">
            <select
              value={newFlag.status}
              onChange={(e) => setNewFlag((p) => ({ ...p, status: e.target.value as FlagStatus }))}
              className="zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <button
              onClick={handleAdd}
              className="zeta-inline-flex zeta-items-center zeta-gap-1.5 zeta-px-3 zeta-py-2 zeta-text-sm zeta-bg-green-600 zeta-text-white zeta-rounded-lg hover:zeta-bg-green-700 zeta-transition-colors"
            >
              <Save className="zeta-w-4 zeta-h-4" />
              저장
            </button>
          </div>
        </div>
      )}

      <div className="zeta-overflow-x-auto zeta-border zeta-border-zeta-border zeta-rounded-xl">
        <table className="zeta-w-full zeta-text-sm">
          <thead className="zeta-bg-zeta-bg-secondary zeta-text-zeta-text-secondary">
            <tr>
              <th className="zeta-px-3 zeta-py-2 zeta-text-left zeta-font-medium">키</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-left zeta-font-medium">레이블</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-left zeta-font-medium">설명</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-center zeta-font-medium">상태</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-center zeta-font-medium">변경</th>
              <th className="zeta-px-3 zeta-py-2 zeta-text-center zeta-font-medium">삭제</th>
            </tr>
          </thead>
          <tbody className="zeta-divide-y zeta-divide-zeta-border">
            {features.map((f) => {
              const s = f.status;
              const Info = ICON_MAP[s];
              return (
                <tr key={f.key} className="zeta-hover:bg-zeta-bg-hover">
                  <td className="zeta-px-3 zeta-py-2 zeta-text-zeta-text zeta-font-mono zeta-text-xs">
                    {f.key}
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-zeta-text zeta-font-medium">
                    {f.label}
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-zeta-text-secondary zeta-text-xs">
                    {f.description}
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-center">
                    <span
                      className={cn(
                        "zeta-inline-flex zeta-items-center zeta-gap-1 zeta-px-2 zeta-py-0.5 zeta-rounded-full zeta-text-xs zeta-font-medium",
                        STATUS_MAP[s].className
                      )}
                    >
                      <Info className="zeta-w-3 zeta-h-3" />
                      {STATUS_MAP[s].label}
                    </span>
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-center">
                    <select
                      value={editStatuses[f.key] || s}
                      onChange={(e) => handleStatusChange(f.key, e.target.value as FlagStatus)}
                      className="zeta-px-2 zeta-py-1 zeta-text-xs zeta-bg-zeta-bg zeta-border zeta-border-zeta-border zeta-rounded-md zeta-text-zeta-text focus:zeta-outline-none focus:zeta-ring-2 focus:zeta-ring-zeta-accent"
                    >
                      {STATUS_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="zeta-px-3 zeta-py-2 zeta-text-center">
                    <button
                      onClick={() => handleDelete(f.key)}
                      className="zeta-p-1 zeta-text-zeta-text-tertiary hover:zeta-text-red-500 zeta-transition-colors"
                    >
                      <Trash2 className="zeta-w-4 zeta-h-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
            {features.length === 0 && (
              <tr>
                <td colSpan={6} className="zeta-px-6 zeta-py-8 zeta-text-center zeta-text-zeta-text-tertiary">
                  등록된 기능 플래그가 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
