"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  HardDrive,
  Download,
  Upload,
  RefreshCw,
  FileJson,
  Shield,
  AlertTriangle,
  Clock,
} from "lucide-react";


interface BackupEntry {
  name: string;
  size: number;
  createdAt: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(d: string) {
  return new Date(d).toLocaleString("ko-KR");
}

export default function AdminBackup() {
  const [backups, setBackups] = useState<BackupEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [restoreConfirm, setRestoreConfirm] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [parsedBackup, setParsedBackup] = useState<{ files: unknown[] } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchBackups = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/backup");
      const data = await res.json();
      setBackups(data.backups ?? data ?? []);
    } catch {
      setBackups([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBackups();
  }, [fetchBackups]);

  async function createBackup() {
    setActionLoading("create");
    try {
      await fetch("/api/admin/backup?action=create", { method: "POST" });
      await fetchBackups();
    } finally {
      setActionLoading(null);
    }
  }

  async function downloadBackup(name: string) {
    window.open(`/api/admin/backup?action=download&name=${encodeURIComponent(name)}`, "_blank");
  }

  async function deleteBackup(name: string) {
    setActionLoading(`delete-${name}`);
    try {
      await fetch("/api/admin/backup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete", name }),
      });
      setBackups((prev) => prev.filter((b) => b.name !== name));
    } finally {
      setActionLoading(null);
    }
  }

  async function restoreBackup(name: string) {
    setActionLoading(`restore-${name}`);
    try {
      await fetch("/api/admin/backup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "restore", name }),
      });
      setRestoreConfirm(null);
    } finally {
      setActionLoading(null);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setUploadError(null);
    setParsedBackup(null);
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadFile(file);

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const json = JSON.parse(reader.result as string);
        if (!json.files || !Array.isArray(json.files)) {
          throw new Error("Invalid backup format");
        }
        setParsedBackup(json);
      } catch {
        setUploadError("유효하지 않은 백업 파일입니다. JSON 형식을 확인하세요.");
      }
    };
    reader.readAsText(file);
  }

  async function uploadAndRestore() {
    if (!uploadFile) return;
    setActionLoading("upload");
    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      await fetch("/api/admin/backup?action=uploadRestore", {
        method: "POST",
        body: formData,
      });
      setUploadFile(null);
      setParsedBackup(null);
      setRestoreConfirm(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="zeta-card p-6 text-center text-zeta-muted">로딩 중...</div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 백업 생성 */}
      <div className="zeta-card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-zeta-accent" />
            <h3 className="text-lg font-semibold text-zeta-text">백업 생성</h3>
          </div>
          <button
            onClick={createBackup}
            disabled={actionLoading === "create"}
            className="zeta-btn zeta-btn-primary text-sm"
          >
            <Shield className="w-4 h-4 mr-1" />
            {actionLoading === "create" ? "생성 중..." : "새 백업 생성"}
          </button>
        </div>
      </div>

      {/* 백업 목록 */}
      <div className="zeta-card p-6">
        <h3 className="text-lg font-semibold text-zeta-text mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-zeta-muted" />
          백업 목록
        </h3>
        {backups.length === 0 ? (
          <p className="text-sm text-zeta-muted">백업 파일이 없습니다.</p>
        ) : (
          <div className="divide-y divide-zeta-border">
            {backups.map((b) => (
              <div
                key={b.name}
                className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="font-medium text-zeta-text truncate">{b.name}</p>
                  <p className="text-sm text-zeta-muted">
                    {formatSize(b.size)} &middot; {formatDate(b.createdAt)}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <button
                    onClick={() => downloadBackup(b.name)}
                    className="zeta-btn zeta-btn-ghost text-sm"
                  >
                    <Download className="w-4 h-4 mr-1" />다운로드
                  </button>
                  <button
                    onClick={() => deleteBackup(b.name)}
                    disabled={actionLoading === `delete-${b.name}`}
                    className="zeta-btn zeta-btn-ghost text-sm text-red-500"
                  >
                    삭제
                  </button>
                  <button
                    onClick={() => setRestoreConfirm(b.name)}
                    disabled={actionLoading === `restore-${b.name}`}
                    className="zeta-btn zeta-btn-ghost text-sm"
                  >
                    <RefreshCw className="w-4 h-4 mr-1" />복원
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 백업 업로드 */}
      <div className="zeta-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Upload className="w-5 h-5 text-zeta-accent" />
          <h3 className="text-lg font-semibold text-zeta-text">백업 업로드</h3>
        </div>
        <div className="flex items-center gap-3">
          <label className="zeta-btn zeta-btn-ghost text-sm cursor-pointer">
            <FileJson className="w-4 h-4 mr-1" />
            JSON 파일 선택
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileChange}
              className="hidden"
            />
          </label>
          {uploadFile && (
            <span className="text-sm text-zeta-muted truncate">{uploadFile.name}</span>
          )}
        </div>
        {uploadError && (
          <p className="text-sm text-red-500 mt-2">{uploadError}</p>
        )}
        {parsedBackup && (
          <div className="mt-4">
            <p className="text-sm text-zeta-muted mb-2">
              {parsedBackup.files.length}개 파일이 포함된 백업입니다.
            </p>
            <button
              onClick={() => setRestoreConfirm("upload")}
              className="zeta-btn zeta-btn-primary text-sm"
            >
              <RefreshCw className="w-4 h-4 mr-1" />이 백업으로 복원
            </button>
          </div>
        )}
      </div>

      {/* 복원 확인 모달 */}
      {restoreConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="zeta-card p-6 max-w-sm w-full mx-4 shadow-xl">
            <div className="flex items-center gap-3 mb-4 text-amber-600">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-semibold text-zeta-text">정말 복원하시겠습니까?</h3>
            </div>
            <p className="text-sm text-zeta-muted mb-6">
              현재 데이터가 덮어쓰기됩니다. 이 작업은 되돌릴 수 없습니다.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setRestoreConfirm(null)}
                className="zeta-btn zeta-btn-ghost text-sm"
              >
                취소
              </button>
              <button
                onClick={() =>
                  restoreConfirm === "upload"
                    ? uploadAndRestore()
                    : restoreBackup(restoreConfirm)
                }
                disabled={actionLoading !== null}
                className="zeta-btn zeta-btn-danger text-sm"
              >
                {actionLoading ? "복원 중..." : "복원"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
