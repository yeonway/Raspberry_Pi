"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import Link from "next/link";
import {
  ArchiveRestore,
  LogOut,
  MessageCirclePlus,
  Settings,
  Shield,
  Trash2,
} from "lucide-react";
import type { AuthUser, Character, ChatRoom } from "@/types/chat";
import { cn } from "@/lib/utils";
import { BotAvatar } from "./BotAvatar";

type ChatSidebarProps = {
  characters: Character[];
  currentUser?: AuthUser | null;
  rooms: ChatRoom[];
  selectedRoomId: string;
  onSelectRoom: (roomId: string) => void;
  onRestoreRoom: (roomId: string) => void;
  onDeleteRoom: (roomId: string) => void;
  onNewChat: (characterId?: string) => void;
  onOpenSettings?: () => void;
  showAdminLink?: boolean;
  onLogout?: () => void;
};

type CharacterGroup = {
  character: Character;
  activeRooms: ChatRoom[];
  archivedRooms: ChatRoom[];
  latestRoom: ChatRoom;
};

export function ChatSidebar({
  characters,
  currentUser,
  rooms,
  selectedRoomId,
  onDeleteRoom,
  onLogout,
  onNewChat,
  onOpenSettings,
  showAdminLink = false,
  onRestoreRoom,
  onSelectRoom,
}: ChatSidebarProps) {
  const characterGroups = useMemo(() => {
    const roomMap = new Map<string, { active: ChatRoom[]; archived: ChatRoom[] }>();
    for (const room of rooms) {
      if (!roomMap.has(room.characterId)) {
        roomMap.set(room.characterId, { active: [], archived: [] });
      }
      const entry = roomMap.get(room.characterId)!;
      if (room.archivedAt) {
        entry.archived.push(room);
      } else {
        entry.active.push(room);
      }
    }
    const groups: CharacterGroup[] = [];
    for (const [characterId, { active, archived }] of roomMap) {
      const character = characters.find((c) => c.id === characterId) ?? characters[0];
      if (!character) continue;
      const allRooms = [...active, ...archived].sort(
        (a, b) => new Date(b.lastMessageAt).getTime() - new Date(a.lastMessageAt).getTime(),
      );
      groups.push({ character, activeRooms: active, archivedRooms: archived, latestRoom: allRooms[0] });
    }
    return groups.sort(
      (a, b) => new Date(b.latestRoom.lastMessageAt).getTime() - new Date(a.latestRoom.lastMessageAt).getTime(),
    );
  }, [rooms, characters]);

  const selectedCharacterId = rooms.find((r) => r.id === selectedRoomId)?.characterId;

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {characterGroups.length ? (
          <div className="space-y-2">
            {characterGroups.map((group) => (
              <AccordionGroup
                character={group.character}
                activeRooms={group.activeRooms}
                archivedRooms={group.archivedRooms}
                key={group.character.id}
                selectedRoomId={selectedRoomId}
                isCharacterSelected={group.character.id === selectedCharacterId}
                onDelete={onDeleteRoom}
                onNewChat={() => onNewChat(group.character.id)}
                onRestore={onRestoreRoom}
                onSelect={onSelectRoom}
              />
            ))}
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-4 px-4 py-12 text-center">
            <MessageCirclePlus size={32} className="text-zeta-soft" />
            <p className="text-sm text-zeta-muted">대화를 시작해보세요</p>
            <button
              className="rounded-lg bg-zeta-accent px-5 py-2.5 text-sm font-semibold text-zeta-buttonText transition hover:brightness-95"
              onClick={() => onNewChat()}
              type="button"
            >
              새 채팅
            </button>
          </div>
        )}
      </div>

      <div className="shrink-0 border-t border-zeta-line p-3 space-y-1">
        {currentUser ? (
          <div className="flex items-center gap-3 rounded-lg px-2 py-2.5">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-zeta-accentSoft text-sm font-bold text-zeta-accent">
              {currentUser.name.slice(0, 1).toUpperCase()}
            </div>
            <span className="min-w-0 flex-1 truncate text-sm font-medium text-zeta-text">
              {currentUser.name}
            </span>
          </div>
        ) : null}

        {showAdminLink ? (
          <Link
            href="/admin"
            className="flex items-center gap-3 rounded-lg px-2 py-2 text-sm text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
          >
            <Shield size={16} />
            관리자
          </Link>
        ) : null}

        {onOpenSettings ? (
          <button
            className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-sm text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            onClick={onOpenSettings}
            type="button"
          >
            <Settings size={16} />
            계정 설정
          </button>
        ) : null}

        {onLogout ? (
          <button
            className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-sm text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
            onClick={onLogout}
            type="button"
          >
            <LogOut size={16} />
            로그아웃
          </button>
        ) : null}
      </div>
    </div>
  );
}

function AccordionGroup({
  character,
  activeRooms,
  archivedRooms,
  selectedRoomId,
  isCharacterSelected,
  onDelete,
  onNewChat,
  onRestore,
  onSelect,
}: {
  character: Character;
  activeRooms: ChatRoom[];
  archivedRooms: ChatRoom[];
  selectedRoomId: string;
  isCharacterSelected: boolean;
  onDelete: (roomId: string) => void;
  onNewChat: () => void;
  onRestore: (roomId: string) => void;
  onSelect: (roomId: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState(0);

  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [activeRooms, archivedRooms]);

  const totalRooms = activeRooms.length + archivedRooms.length;

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border transition-colors",
        isCharacterSelected
          ? "border-zeta-accent/30 bg-zeta-accentSoft/40"
          : "border-zeta-line bg-transparent hover:bg-zeta-panel2/40",
      )}
    >
      <button
        className="flex w-full items-center gap-3 px-3.5 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <BotAvatar character={character} size="md" />
        <span className="min-w-0 flex-1 truncate text-sm font-semibold text-zeta-text">
          {character.name}
        </span>
        <span className="shrink-0 text-xs text-zeta-soft">{totalRooms}</span>
      </button>

      <div
        className="overflow-hidden transition-[max-height] duration-300 ease-in-out"
        style={{ maxHeight: open ? contentHeight : 0 }}
      >
        <div ref={contentRef}>
          <div className="border-t border-zeta-line/50 px-2 pb-2 pt-1">
            {activeRooms.map((room) => (
              <button
                className={cn(
                  "group flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left transition",
                  room.id === selectedRoomId
                    ? "bg-zeta-accentSoft text-zeta-text"
                    : "text-zeta-muted hover:bg-zeta-panel2 hover:text-zeta-text",
                )}
                key={room.id}
                onClick={() => onSelect(room.id)}
                type="button"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium">
                    {room.title}
                  </span>
                  <span className="mt-0.5 block truncate text-[11px] opacity-70">
                    {room.lastMessage}
                  </span>
                </span>
                <span className="shrink-0 text-[10px] text-zeta-soft opacity-0 transition group-hover:opacity-100">
                  {room.lastMessageAt}
                </span>
              </button>
            ))}

            {archivedRooms.length > 0 ? (
              <details className="mt-1.5">
                <summary className="cursor-pointer rounded-lg px-3 py-1.5 text-[11px] font-semibold text-zeta-soft transition hover:text-zeta-muted marker:text-[11px]">
                  보관됨 {archivedRooms.length}
                </summary>
                <div className="mt-1 space-y-0.5">
                  {archivedRooms.map((room) => (
                    <div
                      className="flex items-center rounded-lg px-3 py-1.5 text-[13px] text-zeta-muted"
                      key={room.id}
                    >
                      <button
                        className="min-w-0 flex-1 truncate text-left transition hover:text-zeta-text"
                        onClick={() => onSelect(room.id)}
                        type="button"
                      >
                        [보관] {room.title}
                      </button>
                      <button
                        aria-label="복원"
                        className="ml-1 shrink-0 rounded p-1 text-zeta-soft transition hover:text-zeta-text"
                        onClick={() => onRestore(room.id)}
                        type="button"
                      >
                        <ArchiveRestore size={13} />
                      </button>
                      <button
                        aria-label="삭제"
                        className="ml-0.5 shrink-0 rounded p-1 text-zeta-soft transition hover:text-zeta-error"
                        onClick={() => {
                          if (window.confirm("이 대화를 삭제할까요?")) onDelete(room.id);
                        }}
                        type="button"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </details>
            ) : null}

            <button
              className="mt-1.5 flex w-full items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium text-zeta-soft transition hover:bg-zeta-panel2 hover:text-zeta-text"
              onClick={onNewChat}
              type="button"
            >
              <MessageCirclePlus size={13} />새 대화
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
