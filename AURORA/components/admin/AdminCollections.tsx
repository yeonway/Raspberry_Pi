"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  FolderHeart,
  Globe,
  GripVertical,
  ChevronUp,
  ChevronDown,
  Plus,
  Edit,
  Trash2,
  X,
  Check,
  Loader2,
} from "lucide-react";

interface Character {
  id: string;
  name: string;
  intro: string;
}

interface Props {
  characters: Character[];
}

interface Collection {
  id: string;
  title: string;
  description: string;
  characterIds: string[];
  sortOrder: number;
  isPublic: boolean;
}

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

export default function AdminCollections({ characters }: Props) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [form, setForm] = useState<Omit<Collection, "id">>({
    title: "",
    description: "",
    characterIds: [],
    sortOrder: 0,
    isPublic: false,
  });

  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "getCollections" }),
      });
      const data = await res.json();
      setCollections(data.collections || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  const saveCollection = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const payload = editingId
        ? { action: "saveCollection", id: editingId, ...form }
        : { action: "saveCollection", id: genId(), ...form };
      await fetch("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadCollections();
      resetForm();
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const deleteCollection = async (id: string) => {
    try {
      await fetch("/api/admin/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "deleteCollection", id }),
      });
      setCollections((prev) => prev.filter((c) => c.id !== id));
    } catch {
      // silent
    }
  };

  const resetForm = () => {
    setForm({ title: "", description: "", characterIds: [], sortOrder: 0, isPublic: false });
    setEditingId(null);
    setShowForm(false);
  };

  const startEdit = (col: Collection) => {
    setEditingId(col.id);
    setForm({
      title: col.title,
      description: col.description,
      characterIds: col.characterIds,
      sortOrder: col.sortOrder,
      isPublic: col.isPublic,
    });
    setShowForm(true);
  };

  const toggleCharacter = (charId: string) => {
    setForm((prev) => ({
      ...prev,
      characterIds: prev.characterIds.includes(charId)
        ? prev.characterIds.filter((id) => id !== charId)
        : [...prev.characterIds, charId],
    }));
  };

  const moveCharacter = (charId: string, dir: -1 | 1) => {
    setForm((prev) => {
      const idx = prev.characterIds.indexOf(charId);
      if (idx === -1) return prev;
      const arr = [...prev.characterIds];
      const target = idx + dir;
      if (target < 0 || target >= arr.length) return prev;
      [arr[idx], arr[target]] = [arr[target], arr[idx]];
      return { ...prev, characterIds: arr };
    });
  };

  const sortedCollections = [...collections].sort((a, b) => a.sortOrder - b.sortOrder);

  return (
    <div className="zeta-card border zeta-border rounded-lg">
      <div className="flex items-center justify-between p-4 pb-2">
        <h2 className="font-semibold text-lg flex items-center gap-2">
          <FolderHeart className="w-5 h-5" />
          컬렉션
        </h2>
        <button
          onClick={() => setShowForm(true)}
          className="zeta-btn zeta-btn-primary inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm"
        >
          <Plus className="w-4 h-4" />
          추가
        </button>
      </div>

      <div className="px-4 pb-4">
        {showForm && (
          <div className="zeta-card-inner border zeta-border rounded-lg p-3 mb-4 space-y-2">
            <h3 className="text-sm font-semibold">
              {editingId ? "컬렉션 수정" : "새 컬렉션"}
            </h3>
            <div>
              <label className="text-xs font-medium block mb-0.5">제목</label>
              <input
                value={form.title}
                onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                placeholder="컬렉션 제목..."
                className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-0.5">설명</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                placeholder="컬렉션 설명..."
                rows={2}
                className="zeta-input w-full px-3 py-1.5 border zeta-border rounded-lg text-sm resize-y"
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-0.5">정렬 순서</label>
              <input
                type="number"
                value={form.sortOrder}
                onChange={(e) => setForm((p) => ({ ...p, sortOrder: Number(e.target.value) }))}
                className="zeta-input w-24 px-3 py-1.5 border zeta-border rounded-lg text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium">공개</label>
              <button
                onClick={() => setForm((p) => ({ ...p, isPublic: !p.isPublic }))}
                className={cn(
                  "w-9 h-5 rounded-full transition-colors relative",
                  form.isPublic ? "bg-zeta-accent" : "bg-gray-300"
                )}
              >
                <div
                  className={cn(
                    "w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform",
                    form.isPublic ? "translate-x-4" : "translate-x-0.5"
                  )}
                />
              </button>
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">캐릭터</label>
              <div className="max-h-40 overflow-y-auto border zeta-border rounded-lg divide-y zeta-border">
                {characters.map((c) => {
                  const selected = form.characterIds.includes(c.id);
                  return (
                    <button
                      key={c.id}
                      onClick={() => toggleCharacter(c.id)}
                      className={cn(
                        "w-full flex items-center justify-between px-3 py-1.5 text-sm text-left transition-colors",
                        selected ? "bg-zeta-accent/10" : "hover:bg-gray-50"
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div
                          className={cn(
                            "w-4 h-4 rounded border-2 flex items-center justify-center shrink-0",
                            selected ? "border-zeta-accent bg-zeta-accent" : "border-zeta-border"
                          )}
                        >
                          {selected && <Check className="w-3 h-3 text-white" />}
                        </div>
                        <span className="truncate">{c.name}</span>
                      </div>
                      {selected && (
                        <span className="text-xs zeta-text-muted shrink-0 ml-1">{c.intro?.slice(0, 20)}</span>
                      )}
                    </button>
                  );
                })}
              </div>
              {form.characterIds.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs font-medium">캐릭터 순서</p>
                  {form.characterIds.map((id, i) => {
                    const c = characters.find((ch) => ch.id === id);
                    return (
                      <div key={id} className="flex items-center gap-1 text-sm">
                        <GripVertical className="w-3.5 h-3.5 zeta-text-muted shrink-0" />
                        <span className="flex-1 truncate text-xs">{c?.name || id}</span>
                        <button
                          onClick={() => moveCharacter(id, -1)}
                          disabled={i === 0}
                          className="p-0.5 zeta-text-muted hover:text-zeta-text disabled:opacity-30"
                        >
                          <ChevronUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => moveCharacter(id, 1)}
                          disabled={i === form.characterIds.length - 1}
                          className="p-0.5 zeta-text-muted hover:text-zeta-text disabled:opacity-30"
                        >
                          <ChevronDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="flex gap-2 pt-1">
              <button
                onClick={saveCollection}
                disabled={saving}
                className="zeta-btn zeta-btn-primary px-3 py-1.5 rounded-lg text-sm inline-flex items-center gap-1 disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                {editingId ? "수정" : "추가"}
              </button>
              <button
                onClick={resetForm}
                className="zeta-btn px-3 py-1.5 rounded-lg text-sm border zeta-border inline-flex items-center gap-1"
              >
                <X className="w-4 h-4" />
                취소
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin zeta-text-muted" />
          </div>
        ) : sortedCollections.length === 0 ? (
          <p className="text-sm zeta-text-muted text-center py-8">컬렉션이 없습니다</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {sortedCollections.map((col) => {
              const charCount = col.characterIds.length;
              return (
                <div
                  key={col.id}
                  className="zeta-card-inner border zeta-border rounded-lg p-3 flex flex-col justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold truncate">{col.title}</h3>
                      <div className="flex items-center gap-0.5 shrink-0 ml-1">
                        {col.isPublic && (
                          <Globe className="w-3.5 h-3.5 text-green-500" />
                        )}
                        <button onClick={() => startEdit(col)} className="p-1 zeta-text-muted hover:text-zeta-text">
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteCollection(col.id)}
                          className="p-1 zeta-text-muted hover:text-red-500"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    {col.description && (
                      <p className="text-xs zeta-text-muted line-clamp-2">{col.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t zeta-border">
                    <span className="text-xs zeta-text-muted">캐릭터 {charCount}명</span>
                    {col.isPublic && (
                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                        공개
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
