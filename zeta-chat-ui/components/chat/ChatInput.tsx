"use client";

import { useEffect, useRef, useState, type PointerEvent } from "react";
import { ImagePlus, Mic, Pencil, Play, Square, Undo2, Zap } from "lucide-react";
import { requestSuggestion } from "@/lib/chat-api";
import type { Character, Message } from "@/types/chat";

type ChatInputProps = {
  canSkipTurn?: boolean;
  isSending: boolean;
  onAbort?: () => void;
  onSkipTurn?: () => void;
  onSend: (content: string) => void;
  character?: Character;
  messages?: Message[];
};

export function ChatInput({
  canSkipTurn = false,
  isSending,
  onAbort,
  onSkipTurn,
  onSend,
  character,
  messages = [],
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isSuggesting, setIsSuggesting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const ignoreNextAsteriskClickRef = useRef(false);
  const suggestAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 144)}px`;
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

  const handleSuggest = async () => {
    if (isSuggesting || isSending || !character) {
      return;
    }

    suggestAbortRef.current?.abort();
    const abortController = new AbortController();
    suggestAbortRef.current = abortController;
    setIsSuggesting(true);

    try {
      const currentText = value;
      const result = await requestSuggestion({
        character,
        messages,
        currentInput: currentText,
        signal: abortController.signal,
      });

      if (abortController.signal.aborted) {
        return;
      }

      const textarea = textareaRef.current;
      if (!textarea) {
        return;
      }

      if (result.content) {
        const nextValue = currentText.trim()
          ? `${currentText}${result.content}`
          : result.content;

        setValue(nextValue);
        window.requestAnimationFrame(() => {
          textarea.setSelectionRange(nextValue.length, nextValue.length);
          textarea.focus();
        });
      }
    } catch {
      // silently ignore
    } finally {
      if (suggestAbortRef.current === abortController) {
        suggestAbortRef.current = null;
      }
      setIsSuggesting(false);
    }
  };

  const skipTurn = () => {
    if (!canSkipTurn || isSending || value.trim()) {
      return;
    }

    onSkipTurn?.();
  };

  const hasMessage = Boolean(value.trim());

  return (
    <div className="zeta-input-shell shrink-0 border-t border-white/5 bg-zeta-bg px-2 py-2 sm:px-3">
      <div className="zeta-composer-tools mx-auto flex max-w-3xl items-center gap-2 pb-2">
        <button aria-label="사진 추가" className="grid size-7 place-items-center rounded-md bg-zinc-800 text-zinc-300" type="button"><ImagePlus size={14} /></button>
        <span className="rounded-md bg-zinc-800 px-2 py-1 text-[9px] text-zinc-300">스냅챗 포즈</span>
        <button aria-label="글쓰기 도구" className="ml-auto grid size-7 place-items-center rounded-full bg-zinc-800 text-zinc-300" type="button"><Pencil size={13} /></button>
        <button aria-label="새로고침" className="grid size-7 place-items-center rounded-full bg-zinc-800 text-zinc-300" type="button"><Undo2 size={13} /></button>
      </div>
      <div className="mx-auto flex max-w-3xl min-w-0 items-center gap-2">
        <div className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-lg bg-zeta-panel2 px-3 text-zeta-text shadow-[inset_0_0_0_1px_rgba(255,255,255,0.03)] transition focus-within:shadow-[inset_0_0_0_1px_rgb(var(--zeta-accent))] sm:h-11">
          <textarea
            aria-label="Message input"
            className="max-h-24 min-h-6 flex-1 resize-none bg-transparent px-0 py-1 text-sm font-medium leading-6 text-zeta-text outline-none placeholder:text-zeta-muted disabled:cursor-not-allowed disabled:opacity-60"
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
            className="inline-flex h-8 w-7 shrink-0 items-center justify-center bg-transparent text-xl font-semibold leading-none text-zeta-muted transition hover:text-zeta-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zeta-accent disabled:cursor-not-allowed disabled:opacity-45"
            disabled={isSending}
            onClick={handleAsteriskClick}
            onPointerDown={handleAsteriskPointerDown}
            title="Insert *"
            type="button"
          >
            *
          </button>
          <button
            aria-label="Auto suggest"
            className="inline-flex h-8 w-7 shrink-0 items-center justify-center bg-transparent text-sm font-medium leading-none text-zeta-muted transition hover:text-zeta-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zeta-accent disabled:cursor-not-allowed disabled:opacity-45"
            disabled={isSending || isSuggesting || !character}
            onClick={handleSuggest}
            title="자동 입력"
            type="button"
          >
            <Zap size={15} className={isSuggesting ? "animate-pulse" : ""} />
          </button>
        </div>
        {isSending ? (
          <button
            aria-label="Stop generating"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-zeta-accent text-zeta-buttonText shadow-[0_0_0_1px_rgba(255,255,255,0.08)] transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zeta-accent sm:size-11"
            onClick={onAbort}
            title="Stop generating"
            type="button"
          >
            <Square size={15} fill="currentColor" />
          </button>
        ) : hasMessage ? (
          <button
            aria-label="Send"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-zeta-accent text-zeta-buttonText shadow-[0_0_0_1px_rgba(255,255,255,0.08)] transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zeta-accent disabled:cursor-not-allowed disabled:opacity-45 sm:size-11"
            onClick={submit}
            type="button"
          >
            <Mic size={17} />
          </button>
        ) : (
          <button
            aria-label="Skip turn"
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-zeta-accent text-zeta-buttonText shadow-[0_0_0_1px_rgba(255,255,255,0.08)] transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zeta-accent disabled:cursor-not-allowed disabled:opacity-45 sm:size-11"
            disabled={!canSkipTurn || isSending}
            onClick={skipTurn}
            title="Skip turn"
            type="button"
          >
            <Play size={17} fill="currentColor" />
          </button>
        )}
      </div>
    </div>
  );
}
