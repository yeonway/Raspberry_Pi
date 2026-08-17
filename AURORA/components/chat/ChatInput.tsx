"use client";

import { useEffect, useRef, useState, type PointerEvent } from "react";
import { ArrowUp, SkipForward, Square } from "lucide-react";

type ChatInputProps = {
  canSkipTurn?: boolean;
  isSending: boolean;
  onAbort?: () => void;
  onSkipTurn?: () => void;
  onSend: (content: string) => void;
};

export function ChatInput({
  canSkipTurn = false,
  isSending,
  onAbort,
  onSkipTurn,
  onSend,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const ignoreNextAsteriskClickRef = useRef(false);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 216)}px`;
  }, [value]);

  const submit = () => {
    const content = value.trim();
    if (!content || isSending) {
      return;
    }

    onSend(content);
    setValue("");
  };

  const insertAsterisk = () => {
    const textarea = textareaRef.current;
    if (!textarea || isSending) {
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const nextValue = `${value.slice(0, start)}*${value.slice(end)}`;
    const nextCursor = start + 1;

    setValue(nextValue);
    window.requestAnimationFrame(() => {
      textarea.setSelectionRange(nextCursor, nextCursor);
    });
  };

  const handleAsteriskPointerDown = (
    event: PointerEvent<HTMLButtonElement>,
  ) => {
    event.preventDefault();
    ignoreNextAsteriskClickRef.current = true;
    insertAsterisk();
  };

  const handleAsteriskClick = () => {
    if (ignoreNextAsteriskClickRef.current) {
      ignoreNextAsteriskClickRef.current = false;
      return;
    }

    insertAsterisk();
  };

  const skipTurn = () => {
    if (!canSkipTurn || isSending || value.trim()) {
      return;
    }

    onSkipTurn?.();
  };

  const hasMessage = Boolean(value.trim());

  return (
    <div className="zeta-input-shell shrink-0 border-t border-zeta-line bg-zeta-bg px-2 py-2 sm:px-3">
      <div className="mx-auto flex max-w-3xl min-w-0 items-center gap-2">
        <div className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-lg bg-zeta-panel2 px-3 text-zeta-text shadow-[inset_0_0_0_1px_rgba(255,255,255,0.03)] transition focus-within:shadow-[inset_0_0_0_1px_rgb(var(--zeta-accent))] sm:h-11">
          <textarea
            aria-label="Message input"
            className="max-h-36 min-h-6 flex-1 resize-none bg-transparent px-0 py-1 text-sm font-medium leading-6 text-zeta-text outline-none placeholder:text-zeta-muted disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSending}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder="내용 입력하기"
            ref={textareaRef}
            rows={1}
            value={value}
          />
          <button
            aria-label="Insert asterisk"
            className="inline-flex h-8 w-7 shrink-0 items-center justify-center bg-transparent text-xl font-semibold leading-none text-zeta-muted transition hover:text-zeta-text focus-visible:ring-2 focus-visible:ring-zeta-accent disabled:cursor-not-allowed disabled:opacity-45"
            disabled={isSending}
            onClick={handleAsteriskClick}
            onPointerDown={handleAsteriskPointerDown}
            title="Insert *"
            type="button"
          >
            *
          </button>
        </div>
        {isSending ? (
          <button
            aria-label="Stop generating"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-zeta-accent text-zeta-buttonText shadow-[0_0_0_1px_rgba(255,255,255,0.08)] transition hover:brightness-110 focus-visible:ring-2 focus-visible:ring-zeta-accent focus-visible:ring-offset-2 sm:size-11"
            onClick={onAbort}
            title="Stop generating"
            type="button"
          >
            <Square size={15} fill="currentColor" />
          </button>
        ) : hasMessage ? (
          <button
            aria-label="Send"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-zeta-accent text-zeta-buttonText shadow-[0_0_0_1px_rgba(255,255,255,0.08)] transition hover:brightness-110 focus-visible:ring-2 focus-visible:ring-zeta-accent focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-45 sm:size-11"
            onClick={submit}
            type="button"
          >
            <ArrowUp size={17} />
          </button>
        ) : (
          <button
            aria-label="Skip turn"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-zeta-accent text-zeta-buttonText shadow-[0_0_0_1px_rgba(255,255,255,0.08)] transition hover:brightness-110 focus-visible:ring-2 focus-visible:ring-zeta-accent focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-45 sm:size-11"
            disabled={!canSkipTurn || isSending}
            onClick={skipTurn}
            title="Skip turn"
            type="button"
          >
            <SkipForward size={17} fill="currentColor" />
          </button>
        )}
      </div>
    </div>
  );
}
