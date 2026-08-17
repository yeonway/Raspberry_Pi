"use client";

import { useState } from "react";
import { Check, Copy, Pencil, RefreshCcw, Trash2, X } from "lucide-react";
import type { Character, Message } from "@/types/chat";
import { cn } from "@/lib/utils";
import { BotAvatar } from "./BotAvatar";

type MessageBubbleProps = {
  character: Character;
  message: Message;
  onDelete: (messageId: string) => void;
  onEdit: (messageId: string, content: string) => void;
  onOpenCharacterSettings: () => void;
  onRegenerate: (messageId: string) => void;
};

export function MessageBubble({
  character,
  message,
  onDelete,
  onEdit,
  onOpenCharacterSettings,
  onRegenerate,
}: MessageBubbleProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1000);
  };

  const handleSave = () => {
    const trimmed = draft.trim();
    if (trimmed) {
      onEdit(message.id, trimmed);
      setIsEditing(false);
    }
  };

  return (
    <div
      className={cn(
        "group flex min-w-0 items-end gap-2",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser ? (
        <button
          aria-label="캐릭터 설정"
          className="shrink-0 rounded-full outline-none transition hover:brightness-110 focus-visible:ring-2 focus-visible:ring-zeta-accent focus-visible:ring-offset-2"
          onClick={onOpenCharacterSettings}
          title="캐릭터 설정"
          type="button"
        >
          <BotAvatar character={character} size="sm" />
        </button>
      ) : null}

      <div
        className={cn(
          "flex min-w-0 max-w-[84%] flex-col gap-1 sm:max-w-[72%]",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
          "max-w-full whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5 text-sm leading-6",
            isUser
              ? "rounded-br-sm bg-zeta-userBubble text-zeta-userBubbleText"
              : "zeta-assistant-message rounded-bl-sm border border-zeta-line bg-zeta-assistantBubble text-zeta-assistantBubbleText",
          )}
        >
          {isEditing ? (
            <textarea
              className="min-h-24 w-full min-w-[15rem] resize-none rounded-lg border border-zeta-line bg-zeta-panel p-3 text-sm text-zeta-text outline-none focus:border-zeta-accent"
              onChange={(event) => setDraft(event.target.value)}
              value={draft}
            />
          ) : (
            <>
              {message.content ? renderMessageContent(message.content) : null}
            </>
          )}
        </div>

        <div
          className={cn(
            "flex items-center gap-1 text-zeta-soft opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100",
            isUser ? "flex-row-reverse" : "flex-row",
          )}
        >
          <span className="px-1 text-[11px]">{message.createdAt}</span>
          {isEditing ? (
            <>
              <IconButton label="Save" onClick={handleSave}>
                <Check size={14} />
              </IconButton>
              <IconButton label="Cancel" onClick={() => setIsEditing(false)}>
                <X size={14} />
              </IconButton>
            </>
          ) : (
            <>
              {!isUser ? (
                <IconButton
                  label="Regenerate"
                  onClick={() => onRegenerate(message.id)}
                >
                  <RefreshCcw size={14} />
                </IconButton>
              ) : null}
              <IconButton label={copied ? "Copied" : "Copy"} onClick={handleCopy}>
                <Copy size={14} />
              </IconButton>
              <IconButton label="Edit" onClick={() => setIsEditing(true)}>
                <Pencil size={14} />
              </IconButton>
              <IconButton label="Delete" onClick={() => onDelete(message.id)}>
                <Trash2 size={14} />
              </IconButton>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function renderMessageContent(content: string) {
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  let key = 0;

  while (cursor < content.length) {
    const doubleStar = content.indexOf("**", cursor);
    const quote = content.indexOf('"', cursor);
    const singleStar = content.indexOf("*", cursor);

    let nextType: "**" | '"' | "*" | null = null;
    let nextPos = Infinity;

    if (doubleStar !== -1) { nextPos = doubleStar; nextType = "**"; }
    if (quote !== -1 && quote < nextPos) { nextPos = quote; nextType = '"'; }
    if (singleStar !== -1 && singleStar < nextPos && singleStar !== doubleStar) {
      nextPos = singleStar;
      nextType = "*";
    }

    if (nextType === null) {
      nodes.push(content.slice(cursor));
      break;
    }

    if (nextPos > cursor) {
      nodes.push(content.slice(cursor, nextPos));
    }

    if (nextType === "**") {
      cursor = nextPos + 2;
      const end = content.indexOf("**", cursor);
      if (end === -1) {
        nodes.push(content.slice(nextPos));
        break;
      }
      if (end > cursor) {
        nodes.push(
          <span key={`nar-${key}`} className="font-semibold text-zeta-accent">
            {content.slice(cursor, end)}
          </span>,
        );
        key++;
      } else {
        nodes.push("**");
      }
      cursor = end + 2;
    } else if (nextType === '"') {
      cursor = nextPos + 1;
      const end = content.indexOf('"', cursor);
      if (end === -1) {
        nodes.push(content.slice(nextPos));
        break;
      }
      if (end > cursor) {
        nodes.push(
          <span key={`sp-${key}`} className="font-medium text-zeta-text">
            {content.slice(cursor, end)}
          </span>,
        );
        key++;
      } else {
        nodes.push('""');
      }
      cursor = end + 1;
    } else {
      cursor = nextPos + 1;
      const end = content.indexOf("*", cursor);
      if (end === -1) {
        nodes.push(content.slice(nextPos));
        break;
      }
      if (end > cursor) {
        nodes.push(
          <span key={`it-${key}`} className="italic text-zeta-soft">
            {content.slice(cursor, end)}
          </span>,
        );
        key++;
      } else {
        nodes.push("*");
      }
      cursor = end + 1;
    }
  }

  return nodes;
}

function IconButton({
  children,
  label,
  onClick,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      className="rounded-full border border-zeta-line bg-zeta-panel p-1.5 text-zeta-soft transition hover:bg-zeta-panel2 hover:text-zeta-text"
      onClick={onClick}
      title={label}
      type="button"
    >
      {children}
    </button>
  );
}
