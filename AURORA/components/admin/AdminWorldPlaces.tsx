"use client";

import { useState, useEffect } from "react";
import {
  Globe,
  MapPin,
  Building2,
  Plus,
  Edit,
  Trash2,
  BookOpen,
  History,
  ScrollText,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface World {
  id: string;
  name: string;
  overview: string;
  locations: string;
  organizations: string;
  characters: string;
  history: string;
  events: string;
  rules: string;
  terms: string;
}

interface Place {
  id: string;
  name: string;
  description: string;
  atmosphere: string;
  relatedCharacters: string[];
  relatedScenes: string;
  relatedLorebooks: string;
}

interface Props {
  characters: Array<{ id: string; name: string }>;
  onNotice?: (s: string) => void;
  onError?: (s: string) => void;
}

const emptyWorld: World = {
  id: "",
  name: "",
  overview: "",
  locations: "",
  organizations: "",
  characters: "",
  history: "",
  events: "",
  rules: "",
  terms: "",
};

const emptyPlace: Place = {
  id: "",
  name: "",
  description: "",
  atmosphere: "",
  relatedCharacters: [],
  relatedScenes: "",
  relatedLorebooks: "",
};

export default function AdminWorldPlaces({
  characters,
  onNotice,
  onError,
}: Props) {
  const [tab, setTab] = useState<"세계관" | "장소">("세계관");

  const [worlds, setWorlds] = useState<World[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);
  const [loading, setLoading] = useState(false);

  const [showWorldForm, setShowWorldForm] = useState(false);
  const [editingWorld, setEditingWorld] = useState<World>(emptyWorld);

  const [showPlaceForm, setShowPlaceForm] = useState(false);
  const [editingPlace, setEditingPlace] = useState<Place>(emptyPlace);

  const [deleteConfirm, setDeleteConfirm] = useState<{
    type: "world" | "place";
    id: string;
    name: string;
  } | null>(null);

  const api = async (action: string, body?: unknown) => {
    const payload: Record<string, unknown> = { action };
    if (body && typeof body === "object") Object.assign(payload, body);
    const res = await fetch("/api/admin/content", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "요청 실패");
    return data;
  };

  const loadWorlds = async () => {
    setLoading(true);
    try {
      const data = await api("getWorlds");
      setWorlds(data.worlds || []);
    } catch (e: unknown) {
      onError?.((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const loadPlaces = async () => {
    setLoading(true);
    try {
      const data = await api("getPlaces");
      setPlaces(data.places || []);
    } catch (e: unknown) {
      onError?.((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "세계관") loadWorlds();
    else loadPlaces();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const handleWorldSave = async () => {
    try {
      await api("saveWorld", editingWorld);
      onNotice?.("세계관이 저장되었습니다.");
      setShowWorldForm(false);
      loadWorlds();
    } catch (e: unknown) {
      onError?.((e as Error).message);
    }
  };

  const handlePlaceSave = async () => {
    try {
      await api("savePlace", editingPlace);
      onNotice?.("장소가 저장되었습니다.");
      setShowPlaceForm(false);
      loadPlaces();
    } catch (e: unknown) {
      onError?.((e as Error).message);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await api(
        deleteConfirm.type === "world" ? "deleteWorld" : "deletePlace",
        { id: deleteConfirm.id }
      );
      onNotice?.("삭제되었습니다.");
      setDeleteConfirm(null);
      if (deleteConfirm.type === "world") loadWorlds();
      else loadPlaces();
    } catch (e: unknown) {
      onError?.((e as Error).message);
    }
  };

  const handleCharacterToggle = (charId: string) => {
    setEditingPlace((prev) => ({
      ...prev,
      relatedCharacters: prev.relatedCharacters.includes(charId)
        ? prev.relatedCharacters.filter((c) => c !== charId)
        : [...prev.relatedCharacters, charId],
    }));
  };

  return (
    <div className="zeta-space-y-6">
      <div className="zeta-flex zeta-items-center zeta-gap-2 zeta-border-b zeta-border-zeta-border zeta-pb-3">
        {(["세계관", "장소"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "zeta-px-4 zeta-py-2 zeta-rounded-md zeta-text-sm zeta-font-medium zeta-transition-colors",
              tab === t
                ? "zeta-bg-zeta-primary zeta-text-white"
                : "zeta-text-zeta-muted hover:zeta-bg-zeta-surface-hover"
            )}
          >
            {t === "세계관" ? (
              <Globe className="zeta-inline-block zeta-w-4 zeta-h-4 zeta-mr-1" />
            ) : (
              <MapPin className="zeta-inline-block zeta-w-4 zeta-h-4 zeta-mr-1" />
            )}
            {t}
          </button>
        ))}
      </div>

      {tab === "세계관" && (
        <div className="zeta-space-y-4">
          <div className="zeta-flex zeta-items-center zeta-justify-between">
            <h3 className="zeta-text-lg zeta-font-semibold">
              <BookOpen className="zeta-inline-block zeta-w-5 zeta-h-5 zeta-mr-2" />
              세계관 목록
            </h3>
            <button
              onClick={() => {
                setEditingWorld(emptyWorld);
                setShowWorldForm(true);
              }}
              className="zeta-flex zeta-items-center zeta-gap-1 zeta-bg-zeta-primary zeta-text-white zeta-px-3 zeta-py-1.5 zeta-rounded-md zeta-text-sm hover:zeta-opacity-90"
            >
              <Plus className="zeta-w-4 zeta-h-4" />
              새 세계관
            </button>
          </div>

          {loading && (
            <p className="zeta-text-sm zeta-text-zeta-muted">불러오는 중...</p>
          )}

          <div className="zeta-grid zeta-grid-cols-1 md:zeta-grid-cols-2 zeta-gap-4">
            {worlds.map((w) => (
              <div
                key={w.id}
                className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-p-4 zeta-bg-zeta-surface"
              >
                <div className="zeta-flex zeta-items-start zeta-justify-between">
                  <div className="zeta-flex-1 zeta-min-w-0">
                    <h4 className="zeta-font-semibold zeta-truncate">
                      {w.name}
                    </h4>
                    <p className="zeta-text-sm zeta-text-zeta-muted zeta-line-clamp-2 zeta-mt-1">
                      {w.overview}
                    </p>
                  </div>
                  <div className="zeta-flex zeta-gap-1 zeta-ml-2 zeta-shrink-0">
                    <button
                      onClick={() => {
                        setEditingWorld(w);
                        setShowWorldForm(true);
                      }}
                      className="zeta-p-1 zeta-rounded hover:zeta-bg-zeta-surface-hover zeta-text-zeta-muted"
                      title="수정"
                    >
                      <Edit className="zeta-w-4 zeta-h-4" />
                    </button>
                    <button
                      onClick={() =>
                        setDeleteConfirm({
                          type: "world",
                          id: w.id,
                          name: w.name,
                        })
                      }
                      className="zeta-p-1 zeta-rounded hover:zeta-bg-zeta-surface-hover zeta-text-red-500"
                      title="삭제"
                    >
                      <Trash2 className="zeta-w-4 zeta-h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "장소" && (
        <div className="zeta-space-y-4">
          <div className="zeta-flex zeta-items-center zeta-justify-between">
            <h3 className="zeta-text-lg zeta-font-semibold">
              <Building2 className="zeta-inline-block zeta-w-5 zeta-h-5 zeta-mr-2" />
              장소 목록
            </h3>
            <button
              onClick={() => {
                setEditingPlace(emptyPlace);
                setShowPlaceForm(true);
              }}
              className="zeta-flex zeta-items-center zeta-gap-1 zeta-bg-zeta-primary zeta-text-white zeta-px-3 zeta-py-1.5 zeta-rounded-md zeta-text-sm hover:zeta-opacity-90"
            >
              <Plus className="zeta-w-4 zeta-h-4" />
              새 장소
            </button>
          </div>

          {loading && (
            <p className="zeta-text-sm zeta-text-zeta-muted">불러오는 중...</p>
          )}

          <div className="zeta-grid zeta-grid-cols-1 md:zeta-grid-cols-2 zeta-gap-4">
            {places.map((p) => (
              <div
                key={p.id}
                className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-p-4 zeta-bg-zeta-surface"
              >
                <div className="zeta-flex zeta-items-start zeta-justify-between">
                  <div className="zeta-flex-1 zeta-min-w-0">
                    <h4 className="zeta-font-semibold zeta-truncate">
                      {p.name}
                    </h4>
                    <p className="zeta-text-sm zeta-text-zeta-muted zeta-line-clamp-2 zeta-mt-1">
                      {p.description}
                    </p>
                    <p className="zeta-text-xs zeta-text-zeta-muted zeta-mt-1">
                      분위기: {p.atmosphere}
                    </p>
                  </div>
                  <div className="zeta-flex zeta-gap-1 zeta-ml-2 zeta-shrink-0">
                    <button
                      onClick={() => {
                        setEditingPlace(p);
                        setShowPlaceForm(true);
                      }}
                      className="zeta-p-1 zeta-rounded hover:zeta-bg-zeta-surface-hover zeta-text-zeta-muted"
                      title="수정"
                    >
                      <Edit className="zeta-w-4 zeta-h-4" />
                    </button>
                    <button
                      onClick={() =>
                        setDeleteConfirm({
                          type: "place",
                          id: p.id,
                          name: p.name,
                        })
                      }
                      className="zeta-p-1 zeta-rounded hover:zeta-bg-zeta-surface-hover zeta-text-red-500"
                      title="삭제"
                    >
                      <Trash2 className="zeta-w-4 zeta-h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showWorldForm && (
        <div className="zeta-fixed zeta-inset-0 zeta-z-50 zeta-flex zeta-items-center zeta-justify-center zeta-bg-black/50">
          <div className="zeta-bg-zeta-surface zeta-rounded-xl zeta-shadow-xl zeta-p-6 zeta-w-full zeta-max-w-2xl zeta-max-h-[90vh] zeta-overflow-y-auto">
            <h3 className="zeta-text-lg zeta-font-semibold zeta-mb-4">
              {editingWorld.id ? "세계관 수정" : "새 세계관"}
            </h3>
            <div className="zeta-space-y-3">
              {[
                {
                  key: "name",
                  label: "이름",
                  rows: 1,
                },
                {
                  key: "overview",
                  label: "개요",
                  rows: 3,
                },
                {
                  key: "locations",
                  label: "지역",
                  rows: 3,
                },
                {
                  key: "organizations",
                  label: "조직",
                  rows: 3,
                },
                {
                  key: "characters",
                  label: "인물",
                  rows: 3,
                },
                {
                  key: "history",
                  label: "역사",
                  rows: 3,
                  icon: History,
                },
                {
                  key: "events",
                  label: "사건",
                  rows: 3,
                },
                {
                  key: "rules",
                  label: "규칙",
                  rows: 3,
                },
                {
                  key: "terms",
                  label: "용어",
                  rows: 3,
                  icon: ScrollText,
                },
              ].map(({ key, label, rows, icon: Icon }) => (
                <div key={key}>
                  <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                    {Icon && (
                      <Icon className="zeta-inline-block zeta-w-4 zeta-h-4 zeta-mr-1" />
                    )}
                    {label}
                  </label>
                  <textarea
                    rows={rows}
                    value={
                      (editingWorld as unknown as Record<string, string>)[key]
                    }
                    onChange={(e) =>
                      setEditingWorld((prev) => ({
                        ...prev,
                        [key]: e.target.value,
                      }))
                    }
                    className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg zeta-resize-vertical"
                  />
                </div>
              ))}
            </div>
            <div className="zeta-flex zeta-gap-2 zeta-mt-4">
              <button
                onClick={handleWorldSave}
                className="zeta-bg-zeta-primary zeta-text-white zeta-px-4 zeta-py-2 zeta-rounded-md zeta-text-sm"
              >
                저장
              </button>
              <button
                onClick={() => setShowWorldForm(false)}
                className="zeta-border zeta-border-zeta-border zeta-px-4 zeta-py-2 zeta-rounded-md zeta-text-sm zeta-text-zeta-muted"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}

      {showPlaceForm && (
        <div className="zeta-fixed zeta-inset-0 zeta-z-50 zeta-flex zeta-items-center zeta-justify-center zeta-bg-black/50">
          <div className="zeta-bg-zeta-surface zeta-rounded-xl zeta-shadow-xl zeta-p-6 zeta-w-full zeta-max-w-2xl zeta-max-h-[90vh] zeta-overflow-y-auto">
            <h3 className="zeta-text-lg zeta-font-semibold zeta-mb-4">
              {editingPlace.id ? "장소 수정" : "새 장소"}
            </h3>
            <div className="zeta-space-y-3">
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  이름
                </label>
                <input
                  type="text"
                  value={editingPlace.name}
                  onChange={(e) =>
                    setEditingPlace((prev) => ({
                      ...prev,
                      name: e.target.value,
                    }))
                  }
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg"
                />
              </div>
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  설명
                </label>
                <textarea
                  rows={3}
                  value={editingPlace.description}
                  onChange={(e) =>
                    setEditingPlace((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg zeta-resize-vertical"
                />
              </div>
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  분위기
                </label>
                <textarea
                  rows={2}
                  value={editingPlace.atmosphere}
                  onChange={(e) =>
                    setEditingPlace((prev) => ({
                      ...prev,
                      atmosphere: e.target.value,
                    }))
                  }
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg zeta-resize-vertical"
                />
              </div>
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  관련 인물
                </label>
                <div className="zeta-flex zeta-flex-wrap zeta-gap-2">
                  {characters.map((c) => (
                    <label
                      key={c.id}
                      className="zeta-flex zeta-items-center zeta-gap-1.5 zeta-text-sm zeta-cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={editingPlace.relatedCharacters.includes(c.id)}
                        onChange={() => handleCharacterToggle(c.id)}
                        className="zeta-w-4 zeta-h-4 zeta-text-zeta-primary"
                      />
                      {c.name}
                    </label>
                  ))}
                  {characters.length === 0 && (
                    <p className="zeta-text-xs zeta-text-zeta-muted">
                      등록된 인물이 없습니다.
                    </p>
                  )}
                </div>
              </div>
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  관련 장면
                </label>
                <textarea
                  rows={2}
                  value={editingPlace.relatedScenes}
                  onChange={(e) =>
                    setEditingPlace((prev) => ({
                      ...prev,
                      relatedScenes: e.target.value,
                    }))
                  }
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg zeta-resize-vertical"
                />
              </div>
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  관련 로어북
                </label>
                <textarea
                  rows={2}
                  value={editingPlace.relatedLorebooks}
                  onChange={(e) =>
                    setEditingPlace((prev) => ({
                      ...prev,
                      relatedLorebooks: e.target.value,
                    }))
                  }
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg zeta-resize-vertical"
                />
              </div>
            </div>
            <div className="zeta-flex zeta-gap-2 zeta-mt-4">
              <button
                onClick={handlePlaceSave}
                className="zeta-bg-zeta-primary zeta-text-white zeta-px-4 zeta-py-2 zeta-rounded-md zeta-text-sm"
              >
                저장
              </button>
              <button
                onClick={() => setShowPlaceForm(false)}
                className="zeta-border zeta-border-zeta-border zeta-px-4 zeta-py-2 zeta-rounded-md zeta-text-sm zeta-text-zeta-muted"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="zeta-fixed zeta-inset-0 zeta-z-50 zeta-flex zeta-items-center zeta-justify-center zeta-bg-black/50">
          <div className="zeta-bg-zeta-surface zeta-rounded-xl zeta-shadow-xl zeta-p-6 zeta-w-full zeta-max-w-sm">
            <p className="zeta-text-sm">
              &ldquo;{deleteConfirm.name}&rdquo;을(를) 정말 삭제하시겠습니까?
            </p>
            <div className="zeta-flex zeta-gap-2 zeta-mt-4 zeta-justify-end">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="zeta-border zeta-border-zeta-border zeta-px-3 zeta-py-1.5 zeta-rounded-md zeta-text-sm zeta-text-zeta-muted"
              >
                취소
              </button>
              <button
                onClick={handleDelete}
                className="zeta-bg-red-500 zeta-text-white zeta-px-3 zeta-py-1.5 zeta-rounded-md zeta-text-sm"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
