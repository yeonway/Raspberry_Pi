"use client";

import { useState, useEffect, useCallback } from "react";
import { Trash2, RotateCcw, AlertTriangle, Archive } from "lucide-react";
import { cn } from "@/lib/utils";

interface TrashItem {
  id: string;
  type: string;
  name: string;
  deletedAt: string;
}

const typeColors: Record<string, string> = {
  character: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  conversation: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  lorebook: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  world: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  place: "bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300",
  memory: "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300",
};

function formatDate(d: string) {
  return new Date(d).toLocaleString("ko-KR");
}

export default function AdminTrash() {
  const [items, setItems] = useState<TrashItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [confirmTarget, setConfirmTarget] = useState<{ action: string; id?: string } | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/trash");
      const data = await res.json();
      setItems(data.items ?? data ?? []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  async function doAction(action: string, id?: string) {
    setActionLoading(id ?? "all");
    try {
      await fetch("/api/admin/trash", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, id }),
      });
      if (action === "empty" || action === "permanentDelete") {
        setItems((prev) => (id ? prev.filter((i) => i.id !== id) : []));
      }
    } finally {
      setActionLoading(null);
      setConfirmTarget(null);
    }
  }

  function confirmAction(action: string, id?: string) {
    setConfirmTarget({ action, id });
  }

  if (loading) {
    return (
      <div className="zeta-card p-6 text-center text-zeta-muted">로딩 중...</div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="zeta-card p-12 flex flex-col items-center gap-3 text-zeta-muted">
        <Archive className="w-12 h-12" />
        <p className="text-lg font-medium">휴지통이 비어 있습니다</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zeta-text">휴지통</h2>
        <button
          onClick={() => confirmAction("empty")}
          className="zeta-btn zeta-btn-danger text-sm"
        >
          <Trash2 className="w-4 h-4 mr-1" />
          전체 비우기
        </button>
      </div>

      <div className="zeta-card divide-y divide-zeta-border">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between p-4 hover:bg-zeta-hover transition-colors"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span
                className={cn(
                  "px-2 py-0.5 rounded text-xs font-medium shrink-0",
                  typeColors[item.type] ?? "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                )}
              >
                {item.type}
              </span>
              <span className="font-medium text-zeta-text truncate">{item.name}</span>
              <span className="text-sm text-zeta-muted shrink-0">
                {formatDate(item.deletedAt)}
              </span>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-4">
              <button
                onClick={() => doAction("restore", item.id)}
                disabled={actionLoading === item.id}
                className="zeta-btn zeta-btn-ghost text-sm"
              >
                <RotateCcw className="w-4 h-4 mr-1" />
                복원
              </button>
              <button
                onClick={() => confirmAction("permanentDelete", item.id)}
                disabled={actionLoading === item.id}
                className="zeta-btn zeta-btn-ghost text-sm text-red-500 hover:text-red-600"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                영구 삭제
              </button>
            </div>
          </div>
        ))}
      </div>

      {confirmTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="zeta-card p-6 max-w-sm w-full mx-4 shadow-xl">
            <div className="flex items-center gap-3 mb-4 text-amber-600">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-semibold text-zeta-text">정말 삭제하시겠습니까?</h3>
            </div>
            <p className="text-sm text-zeta-muted mb-6">
              {confirmTarget.action === "empty"
                ? "휴지통의 모든 항목이 영구적으로 삭제됩니다."
                : "이 항목이 영구적으로 삭제됩니다."}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmTarget(null)}
                className="zeta-btn zeta-btn-ghost text-sm"
              >
                취소
              </button>
              <button
                onClick={() => doAction(confirmTarget.action, confirmTarget.id)}
                disabled={actionLoading !== null}
                className="zeta-btn zeta-btn-danger text-sm"
              >
                {actionLoading ? "삭제 중..." : "삭제"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
