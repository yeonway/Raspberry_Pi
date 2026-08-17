import type React from "react";
import { AlertCircle, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatLogEntry, ChatLogSession } from "@/types/chat";

export function AdminNavButton({
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
      className={cn(
        "rounded-lg border px-3 py-2 text-xs font-semibold transition sm:px-4 sm:text-sm",
        active
          ? "border-zeta-accent bg-zeta-accentSoft text-zeta-text"
          : "border-zeta-line bg-zeta-panel text-zeta-muted hover:bg-zeta-panel2",
      )}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

export function Field({
  children,
  className = "",
  label,
}: {
  children: React.ReactNode;
  className?: string;
  label: string;
}) {
  return (
    <label className={`block min-w-0 ${className}`}>
      <span className="mb-1 block text-[11px] font-semibold text-zeta-muted sm:text-xs">
        {label}
      </span>
      {children}
    </label>
  );
}

export function LogMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-zeta-line bg-zeta-panel px-2.5 py-2 sm:px-3">
      <p className="text-[11px] text-zeta-soft sm:text-xs">{label}</p>
      <p className="mt-0.5 text-base font-semibold text-zeta-text sm:mt-1 sm:text-lg">{value}</p>
    </div>
  );
}

export function LogScopeButton({
  active,
  errorCount = 0,
  icon,
  meta,
  onClick,
  subtitle,
  title,
}: {
  active: boolean;
  errorCount?: number;
  icon: React.ReactNode;
  meta: string;
  onClick: () => void;
  subtitle: string;
  title: string;
}) {
  return (
    <button
      className={cn(
        "w-full rounded-lg border p-2.5 text-left transition focus:outline-none focus:ring-2 focus:ring-zeta-accent sm:p-3",
        active
          ? "border-zeta-accent bg-zeta-accentSoft"
          : "border-zeta-line bg-zeta-panel hover:bg-zeta-panel2",
      )}
      onClick={onClick}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-zeta-text sm:gap-2 sm:text-sm">
            <span className="shrink-0 text-zeta-soft">{icon}</span>
            <span className="truncate">{title}</span>
          </p>
          <p className="mt-0.5 truncate text-[11px] text-zeta-soft sm:mt-1 sm:text-xs">{subtitle}</p>
        </div>
        {errorCount ? (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">
            <AlertCircle size={13} />
            {errorCount}
          </span>
        ) : null}
      </div>
      <p className="mt-1.5 truncate text-[11px] text-zeta-muted sm:mt-2 sm:text-xs">{meta}</p>
    </button>
  );
}

export function LogTimelineItem({ log }: { log: ChatLogEntry }) {
  const lastUserMessage = getLastUserMessage(log);
  const hasError = Boolean(log.error);

  return (
    <article className="rounded-lg border border-zeta-line bg-zeta-panel2 p-3 sm:p-4">
      <div className="flex flex-col gap-2 sm:gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-lg border border-zeta-line bg-zeta-panel px-2 py-1 text-xs font-semibold text-zeta-muted">
              <UserRound size={13} />
              {log.sessionName ?? log.userName ?? "Unknown person"}
            </span>
            <span className="inline-flex rounded-lg border border-zeta-line bg-zeta-panel px-2 py-1 text-xs text-zeta-soft">
              {log.characterName}
            </span>
            {hasError ? (
              <span className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">
                <AlertCircle size={13} />
                오류
              </span>
            ) : null}
          </div>
          <h4 className="mt-1.5 truncate text-sm font-semibold text-zeta-text sm:mt-2 sm:text-base">
            {log.chatTitle ?? log.chatId}
          </h4>
          <p className="mt-1 text-xs text-zeta-soft">
            {formatLogDate(log.createdAt)} · {getResponseStyleLabel(log)}
          </p>
        </div>
        <div className="break-all text-xs text-zeta-soft lg:max-w-sm lg:text-right">
          <p>세션 {log.clientSessionId ?? log.sessionId}</p>
          <p>대화 {log.chatId}</p>
        </div>
      </div>

      <div className="mt-3 grid gap-2 sm:mt-4 sm:gap-3 lg:grid-cols-2">
        <LogPreviewBlock
          label="사용자 메시지"
          text={lastUserMessage?.content ?? "사용자 메시지 없음"}
        />
        <LogPreviewBlock
          label={hasError ? "오류" : "응답"}
          text={log.assistantContent ?? log.error ?? "응답 없음"}
        />
      </div>
    </article>
  );
}

export function LogPagination({
  currentPage,
  onPageChange,
  pageCount,
  visiblePages,
}: {
  currentPage: number;
  onPageChange: React.Dispatch<React.SetStateAction<number>>;
  pageCount: number;
  visiblePages: Array<number | string>;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        className="h-9 rounded-lg border border-zeta-line px-3 text-sm text-zeta-muted transition hover:bg-zeta-panel disabled:cursor-not-allowed disabled:opacity-45"
        disabled={currentPage <= 1}
        onClick={() => onPageChange((page) => Math.max(1, page - 1))}
        type="button"
      >
        이전
      </button>
      {visiblePages.map((page) =>
        typeof page === "number" ? (
          <button
            className={cn(
              "h-9 min-w-9 rounded-lg border px-3 text-sm transition",
              page === currentPage
                ? "border-zeta-accent bg-zeta-accentSoft text-zeta-text"
                : "border-zeta-line text-zeta-muted hover:bg-zeta-panel",
            )}
            key={page}
            onClick={() => onPageChange(page)}
            type="button"
          >
            {page}
          </button>
        ) : (
          <span
            className="flex h-9 min-w-9 items-center justify-center text-sm text-zeta-soft"
            key={page}
          >
            ...
          </span>
        ),
      )}
      <button
        className="h-9 rounded-lg border border-zeta-line px-3 text-sm text-zeta-muted transition hover:bg-zeta-panel disabled:cursor-not-allowed disabled:opacity-45"
        disabled={currentPage >= pageCount}
        onClick={() => onPageChange((page) => Math.min(pageCount, page + 1))}
        type="button"
      >
        다음
      </button>
    </div>
  );
}

export function getVisiblePageNumbers(
  currentPage: number,
  pageCount: number,
) {
  const pages = new Set<number>([1, pageCount]);

  for (
    let page = Math.max(1, currentPage - 1);
    page <= Math.min(pageCount, currentPage + 1);
    page += 1
  ) {
    pages.add(page);
  }

  const sortedPages = Array.from(pages).sort((left, right) => left - right);
  const visiblePages: Array<number | string> = [];

  sortedPages.forEach((page, index) => {
    const previousPage = sortedPages[index - 1];
    if (previousPage && page - previousPage > 1) {
      visiblePages.push(`ellipsis-${previousPage}-${page}`);
    }

    visiblePages.push(page);
  });

  return visiblePages;
}

export function getLogSessionSearchText(session: ChatLogSession) {
  return [
    session.name,
    session.userId,
    ...session.sessionIds,
    ...session.chatIds,
    ...session.chatTitles,
    ...session.characterNames,
    session.latestUserMessage,
    session.latestAssistantContent,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function LogPreviewBlock({
  label,
  text,
}: {
  label: string;
  text: string;
}) {
  return (
    <div className="rounded-lg border border-zeta-line bg-zeta-panel p-2.5 sm:p-3">
      <p className="mb-1.5 text-[11px] font-semibold text-zeta-soft sm:mb-2 sm:text-xs">{label}</p>
      <p className="line-clamp-3 whitespace-pre-wrap text-xs leading-5 text-zeta-muted sm:text-sm sm:leading-6">
        {text}
      </p>
    </div>
  );
}

export function formatLogDate(value: string) {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) {
    return value;
  }

  return new Date(timestamp).toLocaleString("ko-KR");
}

function getLastUserMessage(log: ChatLogEntry) {
  return [...log.messages].reverse().find((message) => message.role === "user");
}

function getResponseStyleLabel(log: ChatLogEntry) {
  const flavor = log.responseStyle.flavor === "intense" ? "강하게" : "안전하게";
  const length =
    log.responseStyle.length === "short"
      ? "짧게"
      : log.responseStyle.length === "long"
        ? "길게"
        : "보통";

  return `${flavor} · ${length}`;
}
