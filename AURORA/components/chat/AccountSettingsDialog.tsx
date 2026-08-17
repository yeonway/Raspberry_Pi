"use client";

import { FormEvent, useState } from "react";
import { Brain, Clock, LogOut, Save, UserRound, X } from "lucide-react";
import type { AuthUser, MemoryItem } from "@/types/chat";

type AccountSettingsDialogProps = {
  memories?: MemoryItem[];
  user: AuthUser;
  onClose: () => void;
  onLogout: () => void;
  onUserChange: (user: AuthUser) => void;
};

type ProfileResponse = {
  user?: AuthUser;
  error?: string;
};

type AccountTab = "profile" | "tmi";

export function AccountSettingsDialog({
  memories = [],
  user,
  onClose,
  onLogout,
  onUserChange,
}: AccountSettingsDialogProps) {
  const [activeTab, setActiveTab] = useState<AccountTab>("profile");
  const [name, setName] = useState(user.name);
  const [error, setError] = useState<string | undefined>();
  const [status, setStatus] = useState<string | undefined>();
  const [isSaving, setIsSaving] = useState(false);
  const trimmedName = name.trim().replace(/\s+/g, " ");
  const isNameChanged = trimmedName !== user.name;
  const visibleMemories = memories.slice(0, 80);

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(undefined);
    setStatus(undefined);

    if (!trimmedName) {
      setError("Enter a display name.");
      return;
    }

    setIsSaving(true);
    try {
      const response = await fetch("/api/account/profile", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: trimmedName }),
      });
      const payload = (await response
        .json()
        .catch(() => null)) as ProfileResponse | null;

      if (!response.ok || !payload?.user) {
        throw new Error(payload?.error ?? "Profile could not be saved.");
      }

      onUserChange(payload.user);
      setName(payload.user.name);
      setStatus("Saved.");
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Profile could not be saved.",
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 px-4">
      <section className="w-full max-w-md overflow-hidden rounded-lg border border-zeta-line bg-zeta-panel shadow-zeta">
        <div className="flex items-center justify-between gap-3 border-b border-zeta-line px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-zeta-line bg-zeta-panel2 text-zeta-muted">
              <UserRound size={20} />
            </span>
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-zeta-text">
                Account
              </h2>
              <p className="truncate text-xs text-zeta-muted">{user.name}</p>
            </div>
          </div>
          <button
            aria-label="Close"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-zeta-line text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            onClick={onClose}
            type="button"
          >
            <X size={20} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-1 border-b border-zeta-line p-2">
          <TabButton
            active={activeTab === "profile"}
            label="Profile"
            onClick={() => setActiveTab("profile")}
          />
          <TabButton
            active={activeTab === "tmi"}
            label={`My TMI ${memories.length || ""}`.trim()}
            onClick={() => setActiveTab("tmi")}
          />
        </div>

        {activeTab === "profile" ? (
          <form className="space-y-4 p-4" onSubmit={saveProfile}>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-zeta-muted">
                Display name
              </span>
              <input
                autoComplete="name"
                className="input"
                maxLength={40}
                onChange={(event) => {
                  setName(event.target.value);
                  setError(undefined);
                  setStatus(undefined);
                }}
                required
                value={name}
              />
            </label>

            {error ? (
              <p className="rounded-lg border border-zeta-error/40 bg-zeta-errorSoft px-3 py-2 text-sm text-zeta-error">
                {error}
              </p>
            ) : null}

            {status ? (
              <p className="rounded-lg border border-zeta-success/40 bg-zeta-successSoft px-3 py-2 text-sm text-zeta-success">
                {status}
              </p>
            ) : null}

            <div className="flex flex-wrap justify-between gap-2">
              <button
                className="inline-flex h-10 items-center gap-2 rounded-lg border border-zeta-line px-4 text-sm font-semibold text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
                onClick={onLogout}
                type="button"
              >
                <LogOut size={16} />
                Log out
              </button>
              <button
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-zeta-accent px-4 text-sm font-semibold text-zeta-buttonText transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!isNameChanged || isSaving}
                type="submit"
              >
                <Save size={16} />
                {isSaving ? "Saving" : "Save"}
              </button>
            </div>
          </form>
        ) : (
          <section className="p-4">
            {visibleMemories.length ? (
              <div className="scrollbar-thin max-h-[60vh] space-y-2 overflow-y-auto pr-1">
                {visibleMemories.map((memory) => (
                  <article
                    className="rounded-lg border border-zeta-line bg-zeta-panel2 p-3"
                    key={memory.id}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-zeta-text">
                          {memory.chatTitle}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-zeta-soft">
                          {memory.characterName}
                        </p>
                      </div>
                      <time className="inline-flex shrink-0 items-center gap-1 text-[11px] text-zeta-soft">
                        <Clock size={12} />
                        {formatMemoryDate(memory.recentCreatedAt)}
                      </time>
                    </div>
                    <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-zeta-muted">
                      {memory.summary}
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="grid min-h-44 place-items-center rounded-lg border border-dashed border-zeta-line bg-zeta-panel2 px-4 text-center">
                <div>
                  <Brain className="mx-auto text-zeta-soft" size={24} />
                  <p className="mt-3 text-sm font-semibold text-zeta-text">
                    No saved TMI yet.
                  </p>
                  <p className="mt-1 text-xs leading-5 text-zeta-muted">
                    Saved memories will appear here after chats are stored.
                  </p>
                </div>
              </div>
            )}
          </section>
        )}
      </section>
    </div>
  );
}

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={
        active
          ? "h-10 rounded-lg bg-zeta-accent text-sm font-semibold text-zeta-buttonText"
          : "h-10 rounded-lg text-sm font-semibold text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
      }
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function formatMemoryDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
  }).format(date);
}
