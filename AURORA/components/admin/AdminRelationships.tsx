"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  GitGraph,
  Users,
  Heart,
  Edit,
  Trash2,
  Loader2,
  Check,
  X,
} from "lucide-react";

interface Character {
  id: string;
  name: string;
}

interface Props {
  characters: Character[];
}

interface Relationship {
  id: string;
  fromId: string;
  toId: string;
  relation: string;
  description: string;
  events: string;
  secrets: string;
}

const RELATION_COLORS = [
  "#6366f1", "#ec4899", "#14b8a6", "#f59e0b", "#8b5cf6",
  "#06b6d4", "#ef4444", "#22c55e", "#f97316", "#3b82f6",
];

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function getColorForRelation(relation: string): string {
  let hash = 0;
  for (let i = 0; i < relation.length; i++) {
    hash = relation.charCodeAt(i) + ((hash << 5) - hash);
  }
  return RELATION_COLORS[Math.abs(hash) % RELATION_COLORS.length];
}

export default function AdminRelationships({ characters }: Props) {
  const [activeTab, setActiveTab] = useState<"list" | "graph">("list");
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState<Omit<Relationship, "id">>({
    fromId: "",
    toId: "",
    relation: "",
    description: "",
    events: "",
    secrets: "",
  });
  const [editingId, setEditingId] = useState<string | null>(null);

  const [highlightFrom, setHighlightFrom] = useState<string | null>(null);

  useEffect(() => {
    loadRelationships();
  }, []);

  const loadRelationships = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "getRelationships" }),
      });
      const data = await res.json();
      setRelationships(data.relationships || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  const saveRelationship = async () => {
    if (!form.fromId || !form.toId || !form.relation.trim()) return;
    setSaving(true);
    try {
      const payload = editingId
        ? { action: "saveRelationship", id: editingId, ...form }
        : { action: "saveRelationship", id: genId(), ...form };
      await fetch("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadRelationships();
      resetForm();
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const deleteRelationship = async (id: string) => {
    try {
      await fetch("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "deleteRelationship", id }),
      });
      setRelationships((prev) => prev.filter((r) => r.id !== id));
      if (editingId === id) resetForm();
    } catch {
      // silent
    }
  };

  const resetForm = () => {
    setForm({ fromId: "", toId: "", relation: "", description: "", events: "", secrets: "" });
    setEditingId(null);
  };

  const startEdit = (rel: Relationship) => {
    setEditingId(rel.id);
    setForm({
      fromId: rel.fromId,
      toId: rel.toId,
      relation: rel.relation,
      description: rel.description,
      events: rel.events,
      secrets: rel.secrets,
    });
  };

  const getCharName = (id: string) => characters.find((c) => c.id === id)?.name || id;

  const handleNodeClick = (charId: string) => {
    setHighlightFrom(charId);
    setActiveTab("list");
  };

  const graphRadius = 160;
  const graphCx = 250;
  const graphCy = 220;
  const nodeRadius = 28;

  const nodePositions = characters.map((c, i) => {
    const angle = (2 * Math.PI * i) / characters.length - Math.PI / 2;
    return {
      ...c,
      x: graphCx + graphRadius * Math.cos(angle),
      y: graphCy + graphRadius * Math.sin(angle),
    };
  });

  const relevantRels = relationships.filter((r) =>
    characters.some((c) => c.id === r.fromId) && characters.some((c) => c.id === r.toId)
  );

  const filteredRels = highlightFrom
    ? relationships.filter((r) => r.fromId === highlightFrom || r.toId === highlightFrom)
    : relationships;

  return (
    <div className="zeta-card border zeta-border rounded-lg">
      <div className="zeta-tabs flex border-b zeta-border">
        <button
          onClick={() => setActiveTab("list")}
          className={cn(
            "zeta-tab flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "list"
              ? "zeta-tab-active border-zeta-accent text-zeta-accent"
              : "border-transparent zeta-text-muted hover:text-zeta-text"
          )}
        >
          <Users className="w-4 h-4" />
          관계 목록
        </button>
        <button
          onClick={() => setActiveTab("graph")}
          className={cn(
            "zeta-tab flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "graph"
              ? "zeta-tab-active border-zeta-accent text-zeta-accent"
              : "border-transparent zeta-text-muted hover:text-zeta-text"
          )}
        >
          <GitGraph className="w-4 h-4" />
          관계 그래프
        </button>
      </div>

      <div className="p-4">
        {activeTab === "list" && (
          <div className="space-y-4">
            <div className="zeta-card-inner border zeta-border rounded-lg p-3 space-y-2">
              <h3 className="text-sm font-semibold">
                {editingId ? "관계 수정" : "새 관계 추가"}
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-medium block mb-0.5">From</label>
                  <select
                    value={form.fromId}
                    onChange={(e) => setForm((p) => ({ ...p, fromId: e.target.value }))}
                    className="zeta-input w-full px-2 py-1.5 border zeta-border rounded-lg text-sm"
                  >
                    <option value="">선택...</option>
                    {characters.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium block mb-0.5">To</label>
                  <select
                    value={form.toId}
                    onChange={(e) => setForm((p) => ({ ...p, toId: e.target.value }))}
                    className="zeta-input w-full px-2 py-1.5 border zeta-border rounded-lg text-sm"
                  >
                    <option value="">선택...</option>
                    {characters.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium block mb-0.5">관계명</label>
                <input
                  value={form.relation}
                  onChange={(e) => setForm((p) => ({ ...p, relation: e.target.value }))}
                  placeholder="예: 친구, 연인, 가족..."
                  className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium block mb-0.5">설명</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                  rows={2}
                  className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y"
                />
              </div>
              <div>
                <label className="text-xs font-medium block mb-0.5">공유 이벤트</label>
                <textarea
                  value={form.events}
                  onChange={(e) => setForm((p) => ({ ...p, events: e.target.value }))}
                  rows={2}
                  className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y"
                />
              </div>
              <div>
                <label className="text-xs font-medium block mb-0.5">비밀</label>
                <textarea
                  value={form.secrets}
                  onChange={(e) => setForm((p) => ({ ...p, secrets: e.target.value }))}
                  rows={2}
                  className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={saveRelationship}
                  disabled={saving}
                  className="zeta-btn zeta-btn-primary px-3 py-1.5 rounded-lg text-sm inline-flex items-center gap-1 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  {editingId ? "수정" : "추가"}
                </button>
                {editingId && (
                  <button
                    onClick={resetForm}
                    className="zeta-btn px-3 py-1.5 rounded-lg text-sm border zeta-border"
                  >
                    취소
                  </button>
                )}
              </div>
            </div>

            {highlightFrom && (
              <div className="flex items-center gap-2 text-sm">
                <span className="zeta-text-muted">필터:</span>
                <span className="font-medium">{getCharName(highlightFrom)}</span>
                <button
                  onClick={() => setHighlightFrom(null)}
                  className="zeta-text-muted hover:text-zeta-text"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            <div className="zeta-card-inner border zeta-border rounded-lg divide-y zeta-border">
              {filteredRels.length === 0 ? (
                <p className="text-sm zeta-text-muted text-center py-6">
                  {loading ? "로딩 중..." : "관계가 없습니다"}
                </p>
              ) : (
                filteredRels.map((rel) => (
                  <div key={rel.id} className="px-3 py-2.5 flex items-start justify-between">
                    <div className="space-y-0.5 min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-medium">{getCharName(rel.fromId)}</span>
                        <Heart
                          className="w-3.5 h-3.5 shrink-0"
                          style={{ color: getColorForRelation(rel.relation) }}
                        />
                        <span className="text-sm font-medium">{getCharName(rel.toId)}</span>
                      </div>
                      <p className="text-xs font-medium" style={{ color: getColorForRelation(rel.relation) }}>
                        {rel.relation}
                      </p>
                      {rel.description && (
                        <p className="text-xs zeta-text-muted truncate">{rel.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-0.5 ml-2 shrink-0">
                      <button onClick={() => startEdit(rel)} className="p-1 zeta-text-muted hover:text-zeta-text">
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => deleteRelationship(rel.id)}
                        className="p-1 zeta-text-muted hover:text-red-500"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === "graph" && (
          <div className="space-y-3">
            <p className="text-xs zeta-text-muted">노드를 클릭하면 해당 캐릭터의 관계 목록으로 이동합니다</p>
            <div className="border zeta-border rounded-lg overflow-hidden bg-gray-50">
              <svg viewBox="0 0 500 450" className="w-full h-auto">
                {/* Edges */}
                {relevantRels.map((rel) => {
                  const from = nodePositions.find((n) => n.id === rel.fromId);
                  const to = nodePositions.find((n) => n.id === rel.toId);
                  if (!from || !to) return null;
                  const color = getColorForRelation(rel.relation);
                  const midX = (from.x + to.x) / 2;
                  const midY = (from.y + to.y) / 2;
                  return (
                    <g key={rel.id}>
                      <line
                        x1={from.x}
                        y1={from.y}
                        x2={to.x}
                        y2={to.y}
                        stroke={color}
                        strokeWidth={1.5}
                        strokeOpacity={0.6}
                      />
                      <rect
                        x={midX - 24}
                        y={midY - 9}
                        width={48}
                        height={18}
                        rx={4}
                        fill="white"
                        stroke={color}
                        strokeWidth={1}
                      />
                      <text
                        x={midX}
                        y={midY + 4}
                        textAnchor="middle"
                        fill={color}
                        fontSize={9}
                        fontWeight={500}
                      >
                        {rel.relation}
                      </text>
                    </g>
                  );
                })}

                {/* Nodes */}
                {nodePositions.map((node) => (
                  <g
                    key={node.id}
                    onClick={() => handleNodeClick(node.id)}
                    className="cursor-pointer"
                  >
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={nodeRadius}
                      fill="white"
                      stroke="#6366f1"
                      strokeWidth={2}
                    />
                    <text
                      x={node.x}
                      y={node.y + 4}
                      textAnchor="middle"
                      fill="#1e293b"
                      fontSize={11}
                      fontWeight={600}
                    >
                      {node.name.length > 6 ? node.name.slice(0, 6) + "…" : node.name}
                    </text>
                  </g>
                ))}
              </svg>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-2">
              {[...new Set(relevantRels.map((r) => r.relation))].map((rel) => (
                <div key={rel} className="flex items-center gap-1.5 text-xs">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getColorForRelation(rel) }}
                  />
                  {rel}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
