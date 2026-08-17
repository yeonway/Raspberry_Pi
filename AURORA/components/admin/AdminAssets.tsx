"use client";

import { useState, useEffect } from "react";
import {
  ImageIcon,
  Filter,
  Camera,
  Grid3x3,
  Plus,
  Trash2,
  AlertCircle,
  Link,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Asset {
  id: string;
  name: string;
  type: string;
  url: string;
  usedBy: string[];
}

interface Props {
  onNotice?: (s: string) => void;
  onError?: (s: string) => void;
}

const ASSET_TYPES = [
  "character_image",
  "cover",
  "scene",
  "background",
  "other",
] as const;

const TYPE_LABELS: Record<string, string> = {
  character_image: "캐릭터 이미지",
  cover: "표지",
  scene: "장면",
  background: "배경",
  other: "기타",
};

const TYPE_ICONS: Record<string, typeof ImageIcon> = {
  character_image: Camera,
  cover: ImageIcon,
  scene: Grid3x3,
  background: Grid3x3,
  other: ImageIcon,
};

export default function AdminAssets({ onNotice, onError }: Props) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string>("all");
  const [showForm, setShowForm] = useState(false);
  const [editingAsset, setEditingAsset] = useState<Partial<Asset>>({});
  const [deleteConfirm, setDeleteConfirm] = useState<{
    id: string;
    name: string;
    usedBy: string[];
  } | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");

  const api = async (action: string, body?: Record<string, unknown>) => {
    const res = await fetch("/api/admin/content", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...body }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "요청 실패");
    return data;
  };

  const loadAssets = async () => {
    setLoading(true);
    try {
      const data = await api("getAssets");
      setAssets(data.assets || []);
    } catch (e: unknown) {
      onError?.((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAssets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async () => {
    if (!editingAsset.name?.trim()) {
      onError?.("이름을 입력해주세요.");
      return;
    }
    if (!editingAsset.type) {
      onError?.("유형을 선택해주세요.");
      return;
    }
    if (!editingAsset.url?.trim()) {
      onError?.("URL을 입력해주세요.");
      return;
    }
    try {
      await api("saveAsset", editingAsset as Record<string, unknown>);
      onNotice?.("에셋이 저장되었습니다.");
      setShowForm(false);
      setEditingAsset({});
      setPreviewUrl("");
      loadAssets();
    } catch (e: unknown) {
      onError?.((e as Error).message);
    }
  };

  const handleDeleteRequest = (asset: Asset) => {
    if (asset.usedBy.length > 0) {
      onError?.("사용 중인 에셋은 삭제할 수 없습니다.");
      return;
    }
    setDeleteConfirm({
      id: asset.id,
      name: asset.name,
      usedBy: asset.usedBy,
    });
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await api("deleteAsset", { id: deleteConfirm.id });
      onNotice?.("에셋이 삭제되었습니다.");
      setDeleteConfirm(null);
      loadAssets();
    } catch (e: unknown) {
      onError?.((e as Error).message);
    }
  };

  const handleUrlChange = (url: string) => {
    setEditingAsset((prev) => ({ ...prev, url }));
    setPreviewUrl(url);
  };

  const filteredAssets =
    filterType === "all"
      ? assets
      : assets.filter((a) => a.type === filterType);

  const grouped = filteredAssets.reduce<Record<string, Asset[]>>(
    (acc, a) => {
      if (!acc[a.type]) acc[a.type] = [];
      acc[a.type].push(a);
      return acc;
    },
    {}
  );

  return (
    <div className="zeta-space-y-6">
      <div className="zeta-flex zeta-items-center zeta-justify-between">
        <h3 className="zeta-text-lg zeta-font-semibold">
          <ImageIcon className="zeta-inline-block zeta-w-5 zeta-h-5 zeta-mr-2" />
          에셋 관리
        </h3>
        <button
          onClick={() => {
            setEditingAsset({});
            setPreviewUrl("");
            setShowForm(true);
          }}
          className="zeta-flex zeta-items-center zeta-gap-1 zeta-bg-zeta-primary zeta-text-white zeta-px-3 zeta-py-1.5 zeta-rounded-md zeta-text-sm hover:zeta-opacity-90"
        >
          <Plus className="zeta-w-4 zeta-h-4" />
          새 에셋
        </button>
      </div>

      <div className="zeta-flex zeta-items-center zeta-gap-2 zeta-flex-wrap">
        <Filter className="zeta-w-4 zeta-h-4 zeta-text-zeta-muted" />
        <button
          onClick={() => setFilterType("all")}
          className={cn(
            "zeta-px-3 zeta-py-1 zeta-rounded-full zeta-text-xs zeta-font-medium zeta-transition-colors",
            filterType === "all"
              ? "zeta-bg-zeta-primary zeta-text-white"
              : "zeta-bg-zeta-surface-hover zeta-text-zeta-muted hover:zeta-bg-zeta-border"
          )}
        >
          전체
        </button>
        {ASSET_TYPES.map((t) => {
          const Icon = TYPE_ICONS[t] || ImageIcon;
          return (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={cn(
                "zeta-flex zeta-items-center zeta-gap-1 zeta-px-3 zeta-py-1 zeta-rounded-full zeta-text-xs zeta-font-medium zeta-transition-colors",
                filterType === t
                  ? "zeta-bg-zeta-primary zeta-text-white"
                  : "zeta-bg-zeta-surface-hover zeta-text-zeta-muted hover:zeta-bg-zeta-border"
              )}
            >
              <Icon className="zeta-w-3 zeta-h-3" />
              {TYPE_LABELS[t]}
            </button>
          );
        })}
      </div>

      {loading && (
        <p className="zeta-text-sm zeta-text-zeta-muted">불러오는 중...</p>
      )}

      {Object.entries(grouped).map(([type, items]) => (
        <div key={type} className="zeta-space-y-3">
          <h4 className="zeta-text-sm zeta-font-semibold zeta-text-zeta-muted zeta-uppercase zeta-tracking-wide">
            {TYPE_LABELS[type] || type}
          </h4>
          <div className="zeta-grid zeta-grid-cols-2 sm:zeta-grid-cols-3 md:zeta-grid-cols-4 lg:zeta-grid-cols-5 zeta-gap-3">
            {items.map((asset) => (
              <div
                key={asset.id}
                className="zeta-border zeta-border-zeta-border zeta-rounded-lg zeta-overflow-hidden zeta-bg-zeta-surface"
              >
                <div className="zeta-aspect-square zeta-bg-zeta-surface-hover zeta-flex zeta-items-center zeta-justify-center zeta-relative">
                  {asset.url ? (
                    <img
                      src={asset.url}
                      alt={asset.name}
                      className="zeta-w-full zeta-h-full zeta-object-cover"
                    />
                  ) : (
                    <ImageIcon className="zeta-w-8 zeta-h-8 zeta-text-zeta-muted" />
                  )}
                  <span className="zeta-absolute zeta-top-1.5 zeta-right-1.5 zeta-px-1.5 zeta-py-0.5 zeta-rounded zeta-text-[10px] zeta-font-medium zeta-bg-black/60 zeta-text-white">
                    {TYPE_LABELS[asset.type] || asset.type}
                  </span>
                </div>
                <div className="zeta-p-2.5">
                  <p className="zeta-text-sm zeta-font-medium zeta-truncate">
                    {asset.name}
                  </p>
                  {asset.usedBy.length > 0 && (
                    <p className="zeta-text-xs zeta-text-zeta-muted zeta-mt-1 zeta-truncate">
                      사용: {asset.usedBy.join(", ")}
                    </p>
                  )}
                  <div className="zeta-flex zeta-gap-1 zeta-mt-2">
                    <button
                      onClick={() => {
                        setEditingAsset(asset);
                        setPreviewUrl(asset.url || "");
                        setShowForm(true);
                      }}
                      className="zeta-flex-1 zeta-flex zeta-items-center zeta-justify-center zeta-gap-1 zeta-px-2 zeta-py-1 zeta-rounded zeta-text-xs zeta-border zeta-border-zeta-border hover:zeta-bg-zeta-surface-hover zeta-text-zeta-muted"
                      title="수정"
                    >
                      <Link className="zeta-w-3 zeta-h-3" />
                      수정
                    </button>
                    <button
                      onClick={() => handleDeleteRequest(asset)}
                      className={cn(
                        "zeta-px-2 zeta-py-1 zeta-rounded zeta-text-xs zeta-flex zeta-items-center zeta-gap-1",
                        asset.usedBy.length > 0
                          ? "zeta-text-zeta-muted zeta-cursor-not-allowed"
                          : "zeta-text-red-500 hover:zeta-bg-red-50"
                      )}
                      disabled={asset.usedBy.length > 0}
                      title={
                        asset.usedBy.length > 0
                          ? "사용 중인 에셋은 삭제할 수 없습니다."
                          : "삭제"
                      }
                    >
                      <Trash2 className="zeta-w-3 zeta-h-3" />
                      삭제
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {!loading && filteredAssets.length === 0 && (
        <div className="zeta-text-center zeta-py-8 zeta-text-zeta-muted zeta-text-sm">
          <AlertCircle className="zeta-inline-block zeta-w-5 zeta-h-5 zeta-mb-1" />
          <p>표시할 에셋이 없습니다.</p>
        </div>
      )}

      {showForm && (
        <div className="zeta-fixed zeta-inset-0 zeta-z-50 zeta-flex zeta-items-center zeta-justify-center zeta-bg-black/50">
          <div className="zeta-bg-zeta-surface zeta-rounded-xl zeta-shadow-xl zeta-p-6 zeta-w-full zeta-max-w-md">
            <h3 className="zeta-text-lg zeta-font-semibold zeta-mb-4">
              {editingAsset.id ? "에셋 수정" : "새 에셋"}
            </h3>
            <div className="zeta-space-y-3">
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  이름
                </label>
                <input
                  type="text"
                  value={editingAsset.name || ""}
                  onChange={(e) =>
                    setEditingAsset((prev) => ({
                      ...prev,
                      name: e.target.value,
                    }))
                  }
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg"
                  placeholder="에셋 이름"
                />
              </div>
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  유형
                </label>
                <select
                  value={editingAsset.type || ""}
                  onChange={(e) =>
                    setEditingAsset((prev) => ({
                      ...prev,
                      type: e.target.value,
                    }))
                  }
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg"
                >
                  <option value="">유형 선택...</option>
                  {ASSET_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {TYPE_LABELS[t]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="zeta-block zeta-text-sm zeta-font-medium zeta-mb-1">
                  URL
                </label>
                <input
                  type="text"
                  value={editingAsset.url || ""}
                  onChange={(e) => handleUrlChange(e.target.value)}
                  className="zeta-w-full zeta-border zeta-border-zeta-border zeta-rounded-md zeta-p-2 zeta-text-sm zeta-bg-zeta-bg"
                  placeholder="https://..."
                />
              </div>
              {previewUrl && (
                <div className="zeta-border zeta-border-zeta-border zeta-rounded-md zeta-overflow-hidden zeta-aspect-video zeta-bg-zeta-surface-hover">
                  <img
                    src={previewUrl}
                    alt="미리보기"
                    className="zeta-w-full zeta-h-full zeta-object-cover"
                  />
                </div>
              )}
            </div>
            <div className="zeta-flex zeta-gap-2 zeta-mt-4">
              <button
                onClick={handleSave}
                className="zeta-bg-zeta-primary zeta-text-white zeta-px-4 zeta-py-2 zeta-rounded-md zeta-text-sm"
              >
                저장
              </button>
              <button
                onClick={() => {
                  setShowForm(false);
                  setEditingAsset({});
                  setPreviewUrl("");
                }}
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
