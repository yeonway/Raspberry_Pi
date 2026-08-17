"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Users,
  Bot,
  MessageSquare,
  Brain,
  BookOpen,
  ImageIcon,
  Database,
  HardDrive,
  Archive,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DataMetrics {
  users: number;
  characters: number;
  conversations: number;
  messages: number;
  memories: number;
  lorebooks: number;
  assets: number;
  dbSize: string;
  storageSize: string;
  backupSize: string;
}

const metricsConfig: { key: keyof DataMetrics; label: string; icon: React.ElementType; color: string }[] = [
  { key: "users", label: "사용자", icon: Users, color: "text-blue-500 bg-blue-50 dark:bg-blue-900/20" },
  { key: "characters", label: "캐릭터", icon: Bot, color: "text-purple-500 bg-purple-50 dark:bg-purple-900/20" },
  { key: "conversations", label: "대화", icon: MessageSquare, color: "text-green-500 bg-green-50 dark:bg-green-900/20" },
  { key: "messages", label: "메시지", icon: MessageSquare, color: "text-teal-500 bg-teal-50 dark:bg-teal-900/20" },
  { key: "memories", label: "메모리", icon: Brain, color: "text-pink-500 bg-pink-50 dark:bg-pink-900/20" },
  { key: "lorebooks", label: "로어북", icon: BookOpen, color: "text-amber-500 bg-amber-50 dark:bg-amber-900/20" },
  { key: "assets", label: "에셋", icon: ImageIcon, color: "text-indigo-500 bg-indigo-50 dark:bg-indigo-900/20" },
  { key: "dbSize", label: "DB", icon: Database, color: "text-slate-500 bg-slate-50 dark:bg-slate-800" },
  { key: "storageSize", label: "스토리지", icon: HardDrive, color: "text-orange-500 bg-orange-50 dark:bg-orange-900/20" },
  { key: "backupSize", label: "백업", icon: Archive, color: "text-cyan-500 bg-cyan-50 dark:bg-cyan-900/20" },
];

export default function AdminDataManagement() {
  const [metrics, setMetrics] = useState<DataMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [chatbotsRes, configRes] = await Promise.all([
        fetch("/api/admin/chatbots"),
        fetch("/api/admin/config"),
      ]);
      const chatbots = await chatbotsRes.json();
      const config = await configRes.json();

      setMetrics({
        users: config.users ?? 0,
        characters: Array.isArray(chatbots) ? chatbots.length : chatbots.length ?? 0,
        conversations: config.conversations ?? 0,
        messages: config.messages ?? 0,
        memories: config.memories ?? 0,
        lorebooks: config.lorebooks ?? 0,
        assets: config.assets ?? 0,
        dbSize: config.dbSize ?? "0 B",
        storageSize: config.storageSize ?? "0 B",
        backupSize: config.backupSize ?? "0 B",
      });
    } catch {
      setMetrics(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="zeta-card p-6 text-center text-zeta-muted">로딩 중...</div>
    );
  }

  if (!metrics) {
    return (
      <div className="zeta-card p-6 text-center text-zeta-muted">데이터를 불러올 수 없습니다.</div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-zeta-text">데이터 현황</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        {metricsConfig.map(({ key, label, icon: Icon, color }) => (
          <div key={key} className="zeta-card p-4 flex flex-col items-center gap-2 text-center hover:shadow-md transition-shadow">
            <div className={cn("p-3 rounded-xl", color)}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-2xl font-bold text-zeta-text">{metrics[key]}</p>
              <p className="text-xs text-zeta-muted">{label}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
