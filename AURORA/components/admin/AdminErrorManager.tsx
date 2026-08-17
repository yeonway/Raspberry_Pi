"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bell,
  BellRing,
  Bug,
  AlertCircle,
  CheckCircle2,
  Eye,
  Clock,
  MessageSquare,
  FlaskConical,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AdminError {
  id: string;
  message: string;
  stack?: string;
  timestamp: string;
  status: "new" | "checking" | "resolved" | "ignored";
  conversationId?: string;
}

interface AdminNotification {
  id: string;
  type: "error" | "backup" | "ai" | "parse" | "rate";
  title: string;
  message: string;
  time: string;
  read: boolean;
}

const statusTabs = [
  { key: "all", label: "전체" },
  { key: "new", label: "신규" },
  { key: "checking", label: "확인 중" },
  { key: "resolved", label: "해결" },
  { key: "ignored", label: "무시" },
] as const;

const statusLabels: Record<string, string> = {
  new: "신규",
  checking: "확인 중",
  resolved: "해결",
  ignored: "무시",
};

const statusColors: Record<string, string> = {
  new: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  checking: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  resolved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  ignored: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
};

const notifTypeIcons: Record<string, React.ElementType> = {
  error: Bug,
  backup: Clock,
  ai: FlaskConical,
  parse: AlertCircle,
  rate: AlertCircle,
};

const notifTypeColors: Record<string, string> = {
  error: "text-red-500 bg-red-50 dark:bg-red-900/20",
  backup: "text-blue-500 bg-blue-50 dark:bg-blue-900/20",
  ai: "text-amber-500 bg-amber-50 dark:bg-amber-900/20",
  parse: "text-purple-500 bg-purple-50 dark:bg-purple-900/20",
  rate: "text-orange-500 bg-orange-50 dark:bg-orange-900/20",
};

const LS_ERRORS_KEY = "admin-error-manager-state";

export default function AdminErrorManager() {
  const [tab, setTab] = useState<"errors" | "notifications">("errors");
  const [errors, setErrors] = useState<AdminError[]>([]);
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorFilter, setErrorFilter] = useState<string>("all");
  const [statusLoading, setStatusLoading] = useState<string | null>(null);

  const saveErrorsToLS = useCallback((data: AdminError[]) => {
    try {
      localStorage.setItem(LS_ERRORS_KEY, JSON.stringify(data));
    } catch {}
  }, []);

  const loadErrorsFromLS = useCallback((): AdminError[] => {
    try {
      const raw = localStorage.getItem(LS_ERRORS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/config");
      const data = await res.json();
      const fetchedErrors: AdminError[] = data.errors ?? [];
      const merged = fetchedErrors.map((fe) => {
        const cached = loadErrorsFromLS().find((c) => c.id === fe.id);
        return cached?.status && cached.status !== fe.status ? { ...fe, status: cached.status } : fe;
      });
      setErrors(merged);
      setNotifications(data.notifications ?? []);
    } catch {
      setErrors(loadErrorsFromLS());
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [loadErrorsFromLS]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function changeErrorStatus(id: string, status: string) {
    setStatusLoading(id);
    const updated = errors.map((e) => (e.id === id ? { ...e, status: status as AdminError["status"] } : e));
    setErrors(updated);
    saveErrorsToLS(updated);
    try {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "updateErrorStatus", id, status }),
      });
    } catch {}
    setStatusLoading(null);
  }

  async function markNotifRead(id: string) {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    try {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "markNotifRead", id }),
      });
    } catch {}
  }

  async function markAllNotifsRead() {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    try {
      await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "markAllNotifsRead" }),
      });
    } catch {}
  }

  const filteredErrors = errorFilter === "all" ? errors : errors.filter((e) => e.status === errorFilter);
  const unreadCount = notifications.filter((n) => !n.read).length;

  if (loading) {
    return (
      <div className="zeta-card p-6 text-center text-zeta-muted">로딩 중...</div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex gap-2 border-b border-zeta-border pb-2">
        <button
          onClick={() => setTab("errors")}
          className={cn(
            "zeta-btn zeta-btn-ghost text-sm",
            tab === "errors" && "border-b-2 border-zeta-accent text-zeta-accent rounded-none"
          )}
        >
          <Bug className="w-4 h-4 mr-1" />오류 관리
        </button>
        <button
          onClick={() => setTab("notifications")}
          className={cn(
            "zeta-btn zeta-btn-ghost text-sm relative",
            tab === "notifications" && "border-b-2 border-zeta-accent text-zeta-accent rounded-none"
          )}
        >
          <Bell className="w-4 h-4 mr-1" />알림
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* Error Management */}
      {tab === "errors" && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            {statusTabs.map((s) => (
              <button
                key={s.key}
                onClick={() => setErrorFilter(s.key)}
                className={cn(
                  "px-3 py-1 rounded text-sm transition-colors",
                  errorFilter === s.key
                    ? "bg-zeta-accent text-white"
                    : "bg-zeta-muted/10 text-zeta-muted hover:bg-zeta-muted/20"
                )}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div className="zeta-card divide-y divide-zeta-border">
            {filteredErrors.length === 0 ? (
              <p className="p-6 text-center text-sm text-zeta-muted">오류가 없습니다.</p>
            ) : (
              filteredErrors.map((err) => (
                <div key={err.id} className="p-4 hover:bg-zeta-hover transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded text-xs font-medium",
                            statusColors[err.status] ?? statusColors.new
                          )}
                        >
                          {statusLabels[err.status]}
                        </span>
                        <span className="text-sm font-medium text-zeta-text truncate">
                          {err.message}
                        </span>
                      </div>
                      {err.stack && (
                        <pre className="mt-2 text-xs text-zeta-muted bg-zeta-muted/5 p-2 rounded overflow-auto max-h-24">
                          {err.stack}
                        </pre>
                      )}
                      <p className="text-xs text-zeta-muted mt-1">
                        {new Date(err.timestamp).toLocaleString("ko-KR")}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <select
                        value={err.status}
                        onChange={(e) => changeErrorStatus(err.id, e.target.value)}
                        disabled={statusLoading === err.id}
                        className="text-xs zeta-input py-1 px-2 rounded"
                      >
                        {statusTabs.filter((s) => s.key !== "all").map((s) => (
                          <option key={s.key} value={s.key}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                      {err.conversationId && (
                        <a
                          href={`/chat/${err.conversationId}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="zeta-btn zeta-btn-ghost text-xs"
                        >
                          <MessageSquare className="w-3 h-3 mr-1" />대화 열기
                        </a>
                      )}
                      <a
                        href={`/test?error=${err.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="zeta-btn zeta-btn-ghost text-xs"
                      >
                        <FlaskConical className="w-3 h-3 mr-1" />테스트실 재현
                      </a>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Notifications */}
      {tab === "notifications" && (
        <div className="space-y-4">
          {notifications.length > 0 && (
            <div className="flex justify-end">
              <button
                onClick={markAllNotifsRead}
                className="zeta-btn zeta-btn-ghost text-sm"
              >
                <CheckCircle2 className="w-4 h-4 mr-1" />전체 읽음
              </button>
            </div>
          )}

          <div className="grid gap-3">
            {notifications.length === 0 ? (
              <div className="zeta-card p-6 text-center text-sm text-zeta-muted">
                <BellRing className="w-8 h-8 mx-auto mb-2 opacity-50" />
                알림이 없습니다.
              </div>
            ) : (
              notifications.map((notif) => {
                const Icon = notifTypeIcons[notif.type] ?? Bell;
                return (
                  <div
                    key={notif.id}
                    className={cn(
                      "zeta-card p-4 flex items-start gap-3 transition-colors cursor-pointer",
                      !notif.read && "ring-1 ring-zeta-accent/50 bg-zeta-accent/5"
                    )}
                    onClick={() => !notif.read && markNotifRead(notif.id)}
                  >
                    <div className={cn("p-2 rounded-lg shrink-0", notifTypeColors[notif.type])}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-sm text-zeta-text truncate">
                          {notif.title}
                        </h4>
                        {!notif.read && (
                          <span className="w-2 h-2 rounded-full bg-zeta-accent shrink-0" />
                        )}
                      </div>
                      <p className="text-sm text-zeta-muted mt-0.5">{notif.message}</p>
                      <p className="text-xs text-zeta-muted mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(notif.time).toLocaleString("ko-KR")}
                      </p>
                    </div>
                    {!notif.read && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          markNotifRead(notif.id);
                        }}
                        className="zeta-btn zeta-btn-ghost text-xs shrink-0"
                      >
                        <Eye className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
