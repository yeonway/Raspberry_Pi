"use client";

import { FormEvent, useState } from "react";
import type { AccountChatState, AuthUser } from "@/types/chat";

type AuthResponse = {
  user?: AuthUser;
  state?: AccountChatState;
  error?: string;
};

type AuthPanelProps = {
  appName: string;
  onAuthenticated: (user: AuthUser, state?: AccountChatState) => void;
};

export function AuthPanel({ appName, onAuthenticated }: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(undefined);
    setIsSubmitting(true);

    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          password,
        }),
      });
      const payload = (await response.json().catch(() => null)) as
        | AuthResponse
        | null;

      if (!response.ok || !payload?.user) {
        throw new Error(payload?.error ?? "인증에 실패했습니다.");
      }

      onAuthenticated(payload.user, payload.state);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "인증에 실패했습니다.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="grid min-h-dvh place-items-center bg-zeta-bg px-4 text-zeta-text">
      <section className="w-full max-w-sm rounded-lg border border-zeta-line bg-zeta-panel p-6 shadow-zeta">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zeta-soft">
            {appName}
          </p>
          <h1 className="mt-2 text-2xl font-semibold">
            {mode === "login" ? "로그인" : "회원가입"}
          </h1>
        </div>

        <form className="space-y-3" onSubmit={submit}>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-zeta-muted">
              이름
            </span>
            <input
              autoComplete="username"
              className="input"
              minLength={1}
              onChange={(event) => setName(event.target.value)}
              required
              value={name}
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-zeta-muted">
              비밀번호
            </span>
            <input
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              className="input"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? (
            <p className="rounded-lg border border-zeta-error/40 bg-zeta-errorSoft px-3 py-2 text-sm text-zeta-error">
              {error}
            </p>
          ) : null}

          <button
            className="h-11 w-full rounded-lg bg-zeta-accent text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting
              ? "처리 중..."
              : mode === "login"
                ? "로그인"
                : "가입하기"}
          </button>
        </form>

        <button
          className="mt-4 w-full text-sm font-medium text-zeta-muted hover:text-zeta-text"
          onClick={() => {
            setError(undefined);
            setMode(mode === "login" ? "register" : "login");
          }}
          type="button"
        >
          {mode === "login" ? "새 계정 만들기" : "이미 계정이 있습니다"}
        </button>
      </section>
    </main>
  );
}
