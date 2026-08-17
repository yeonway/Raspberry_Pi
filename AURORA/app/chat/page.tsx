"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AuthPanel } from "@/components/chat/AuthPanel";
import { ChatLayout } from "@/components/chat/ChatLayout";
import type { AccountChatState, AuthUser } from "@/types/chat";

function ChatContent() {
  const searchParams = useSearchParams();
  const initialCharacterId = searchParams.get("character") ?? undefined;
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [accountState, setAccountState] = useState<AccountChatState | undefined>();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        const response = await fetch("/api/auth/session", { cache: "no-store" });
        const payload = (await response.json().catch(() => null)) as {
          user: AuthUser | null;
          state: AccountChatState;
        } | null;

        if (cancelled) return;

        if (payload?.user) {
          setCurrentUser(payload.user);
          setAccountState(payload.state);
        } else {
          setCurrentUser(null);
        }
      } catch {
        if (!cancelled) setCurrentUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadSession();
    return () => { cancelled = true; };
  }, []);

  const appName = process.env.NEXT_PUBLIC_APP_NAME ?? "Zeta";

  if (isLoading) {
    return (
      <main className="grid min-h-dvh place-items-center bg-zeta-bg text-sm text-zeta-muted">
        불러오는 중...
      </main>
    );
  }

  if (!currentUser) {
    return (
      <AuthPanel appName={appName} onAuthenticated={(user, state) => {
        setCurrentUser(user);
        setAccountState(state);
      }} />
    );
  }

  return (
    <ChatLayout
      initialUser={currentUser}
      initialAccountState={accountState}
      initialCharacterId={initialCharacterId}
    />
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <main className="grid min-h-dvh place-items-center bg-zeta-bg text-sm text-zeta-muted">
        불러오는 중...
      </main>
    }>
      <ChatContent />
    </Suspense>
  );
}
