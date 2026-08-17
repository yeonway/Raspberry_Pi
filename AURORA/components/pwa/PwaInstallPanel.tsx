"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Download,
  ExternalLink,
  MonitorDown,
  PlusSquare,
  Smartphone,
} from "lucide-react";
import Link from "next/link";

type PromptOutcome = "accepted" | "dismissed";

type BeforeInstallPromptEvent = Event & {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: PromptOutcome; platform: string }>;
  prompt: () => Promise<void>;
};

function isBeforeInstallPromptEvent(
  event: Event,
): event is BeforeInstallPromptEvent {
  return "prompt" in event && "userChoice" in event;
}

function isStandaloneMode() {
  if (typeof window === "undefined") {
    return false;
  }

  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.matchMedia("(display-mode: fullscreen)").matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone ===
      true
  );
}

function isIosBrowser() {
  if (typeof navigator === "undefined") {
    return false;
  }

  return /iPad|iPhone|iPod/.test(navigator.userAgent);
}

export function PwaInstallPanel() {
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isIos, setIsIos] = useState(false);
  const [status, setStatus] = useState("확인 중");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsInstalled(isStandaloneMode());
    setIsIos(isIosBrowser());

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        setError("오프라인 실행 준비에 실패했습니다. 새로고침 후 다시 시도하세요.");
      });
    }

    const handleBeforeInstallPrompt = (event: Event) => {
      if (!isBeforeInstallPromptEvent(event)) {
        return;
      }

      event.preventDefault();
      setInstallPrompt(event);
      setStatus("설치 가능");
    };

    const handleInstalled = () => {
      setInstallPrompt(null);
      setIsInstalled(true);
      setStatus("설치 완료");
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.removeEventListener(
        "beforeinstallprompt",
        handleBeforeInstallPrompt,
      );
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  useEffect(() => {
    if (isInstalled) {
      setStatus("설치 완료");
      return;
    }

    if (installPrompt) {
      setStatus("설치 가능");
      return;
    }

    if (isIos) {
      setStatus("공유 메뉴에서 추가");
      return;
    }

    setStatus("브라우저 메뉴에서 설치");
  }, [installPrompt, isInstalled, isIos]);

  const installButtonLabel = useMemo(() => {
    if (isInstalled) {
      return "설치됨";
    }

    if (installPrompt) {
      return "앱 설치";
    }

    return "설치 대기 중";
  }, [installPrompt, isInstalled]);

  async function handleInstall() {
    if (!installPrompt || isInstalled) {
      return;
    }

    setError(null);
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    setInstallPrompt(null);

    if (choice.outcome === "accepted") {
      setIsInstalled(true);
      setStatus("설치 완료");
      return;
    }

    setStatus("설치 취소됨");
  }

  return (
    <main className="min-h-dvh bg-zeta-bg px-4 py-5 text-zeta-text sm:px-6 sm:py-8">
      <section className="mx-auto flex min-h-[calc(100dvh-2.5rem)] w-full max-w-3xl flex-col justify-center gap-5 sm:min-h-[calc(100dvh-4rem)]">
        <div className="flex items-center justify-between gap-3 border-b border-zeta-line pb-4">
          <span className="rounded-full border border-zeta-line bg-zeta-panel px-3 py-1 text-xs font-semibold text-zeta-muted">
            {status}
          </span>
          <Link
            href="/"
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-zeta-line px-3 text-sm font-semibold text-zeta-muted transition hover:bg-zeta-panel hover:text-zeta-text"
          >
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
            채팅 열기
          </Link>
        </div>

        <div className="rounded-lg border border-zeta-line bg-zeta-panel p-5 shadow-zeta sm:p-7">
          <div className="mb-5 flex size-14 items-center justify-center rounded-lg bg-zeta-accent text-zeta-buttonText">
            <MonitorDown className="size-7" aria-hidden="true" />
          </div>

          <h1 className="text-2xl font-semibold text-zeta-text sm:text-3xl">
            앱처럼 열기
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-6 text-zeta-muted">
            홈 화면이나 데스크톱에 추가하면 주소창 없이 바로 채팅으로 들어갈 수 있습니다.
          </p>

          <div className="mt-6 flex flex-wrap gap-2">
            <Link
              href="/"
              className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-zeta-accent px-4 text-sm font-semibold text-zeta-buttonText shadow-glow transition hover:brightness-95"
            >
              <ExternalLink className="h-5 w-5" aria-hidden="true" />
              지금 채팅하기
            </Link>
            <button
              type="button"
              onClick={handleInstall}
              disabled={!installPrompt || isInstalled}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-lg border border-zeta-line px-4 text-sm font-semibold text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isInstalled ? (
                <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
              ) : (
                <Download className="h-5 w-5" aria-hidden="true" />
              )}
              {installButtonLabel}
            </button>
          </div>

          {error ? (
            <p className="mt-4 rounded-lg border border-red-300/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          {!installPrompt && !isInstalled ? (
            <div className="mt-5 rounded-lg border border-zeta-line bg-zeta-panel2 p-4 text-sm leading-6 text-zeta-muted">
              {isIos ? (
                <p>
                  Safari 공유 버튼을 누른 뒤 <strong>홈 화면에 추가</strong>를 선택하세요.
                </p>
              ) : (
                <p>
                  주소창 또는 브라우저 메뉴의 설치 아이콘을 사용할 수 있습니다.
                </p>
              )}
            </div>
          ) : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-zeta-line bg-zeta-panel p-4">
            <Smartphone className="mb-3 h-5 w-5 text-zeta-accent" aria-hidden="true" />
            <p className="text-sm font-semibold text-zeta-text">모바일</p>
            <p className="mt-1 text-sm leading-6 text-zeta-muted">
              홈 화면 아이콘으로 바로 실행합니다.
            </p>
          </div>
          <div className="rounded-lg border border-zeta-line bg-zeta-panel p-4">
            <PlusSquare className="mb-3 h-5 w-5 text-zeta-accent" aria-hidden="true" />
            <p className="text-sm font-semibold text-zeta-text">데스크톱</p>
            <p className="mt-1 text-sm leading-6 text-zeta-muted">
              독립 창으로 열어 채팅창만 남길 수 있습니다.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
