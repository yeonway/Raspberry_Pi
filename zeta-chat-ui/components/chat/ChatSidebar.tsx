"use client";

import { useCallback, useMemo, useState } from "react";
import {
  Archive,
  ArchiveRestore,
  ChevronDown,
  ChevronRight,
  LogOut,
  MessageCirclePlus,
  PanelLeftClose,
  Search,
  Trash2,
} from "lucide-react";
import type { AuthUser, Character, ChatRoom, MemoryItem } from "@/types/chat";
import { cn } from "@/lib/utils";
import { BotAvatar } from "./BotAvatar";

type ChatSidebarProps = {
  appName: string;
  characters: Character[];
  currentUser?: AuthUser | null;
  memories?: MemoryItem[];
  rooms: ChatRoom[];
  selectedRoomId: string;
  onSelectRoom: (roomId: string) => void;
  onArchiveRoom: (roomId: string) => void;
  onRestoreRoom: (roomId: string) => void;
  onDeleteRoom: (roomId: string) => void;
  onCollapse?: () => void;
  onNewChat: (characterId?: string) => void;
  onLogout?: () => void;
};

export function ChatSidebar({
  appName,
  characters,
  currentUser,
  memories = [],
  rooms,
  selectedRoomId,
  onArchiveRoom,
  onDeleteRoom,
  onLogout,
  onCollapse,
  onNewChat,
  onRestoreRoom,
  onSelectRoom,
}: ChatSidebarProps) {
  const [query, setQuery] = useState("");
  const [isArchiveOpen, setIsArchiveOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);

  const getCharacter = useCallback(
    (characterId: string) => {
      const character =
        characters.find((item) => item.id === characterId) ?? characters[0];
      if (!character) {
        throw new Error("At least one chatbot is required.");
      }
      return character;
    },
    [characters],
  );

  const roomMatchesQuery = useCallback(
    (room: ChatRoom, normalizedQuery: string) => {
      if (!normalizedQuery) {
        return true;
      }

      const character = getCharacter(room.characterId);
      return [character.name, room.title, room.lastMessage]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery);
    },
    [getCharacter],
  );

  const { archivedRooms, activeRooms } = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const visibleRooms = rooms.filter((room) =>
      roomMatchesQuery(room, normalizedQuery),
    );

    return {
      activeRooms: visibleRooms.filter((room) => !room.archivedAt),
      archivedRooms: visibleRooms.filter((room) => room.archivedAt),
    };
  }, [query, rooms, roomMatchesQuery]);

  const confirmDelete = (roomId: string) => {
    if (window.confirm("Delete this chat permanently?")) {
      onDeleteRoom(roomId);
    }
  };

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
      <div className="border-b border-zeta-line p-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-zeta-soft">
              {appName}
            </p>
            <h2 className="mt-1 text-lg font-semibold text-zeta-text">Chat</h2>
          </div>
          <div className="flex items-center gap-2">
            {onCollapse ? (
              <button
                aria-label="Collapse chat list"
                className="inline-flex size-10 items-center justify-center rounded-full border border-zeta-line bg-zeta-panel text-zeta-muted transition hover:bg-zeta-panel2"
                onClick={onCollapse}
                title="Collapse chat list"
                type="button"
              >
                <PanelLeftClose size={17} />
              </button>
            ) : null}
          </div>
        </div>

        <label className="flex h-10 items-center gap-2 rounded-full border border-zeta-line bg-zeta-panel2 px-3 text-zeta-soft">
          <Search size={16} />
          <input
            className="min-w-0 flex-1 bg-transparent text-sm text-zeta-text outline-none placeholder:text-zeta-soft"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search"
            type="search"
            value={query}
          />
        </label>
      </div>

      <div className="border-b border-zeta-line p-3">
        <div className="mb-2 text-xs font-semibold text-zeta-soft">
          Characters
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {characters.map((character) => (
            <button
              className="flex min-w-16 flex-col items-center gap-1 rounded-lg px-2 py-2 text-center text-xs text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
              key={character.id}
              onClick={() => onNewChat(character.id)}
              type="button"
            >
              <BotAvatar character={character} size="sm" />
              <span className="max-w-16 truncate">{character.name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {activeRooms.length ? (
            activeRooms.map((room) => (
              <RoomRow
                character={getCharacter(room.characterId)}
                key={room.id}
                room={room}
                selected={room.id === selectedRoomId}
                onArchive={() => onArchiveRoom(room.id)}
                onDelete={() => confirmDelete(room.id)}
                onSelect={() => onSelectRoom(room.id)}
              />
            ))
          ) : (
            <p className="rounded-lg border border-dashed border-zeta-line px-3 py-4 text-center text-xs text-zeta-soft">
              No active chats.
            </p>
          )}
        </div>

        <section className="mt-3 border-t border-zeta-line pt-3">
          <button
            aria-expanded={isArchiveOpen}
            className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-2 text-left text-xs font-semibold text-zeta-soft transition hover:bg-zeta-panel2 hover:text-zeta-text"
            onClick={() => setIsArchiveOpen((current) => !current)}
            type="button"
          >
            <span className="inline-flex min-w-0 items-center gap-2">
              {isArchiveOpen ? (
                <ChevronDown size={15} />
              ) : (
                <ChevronRight size={15} />
              )}
              <span>Archived</span>
            </span>
            <span className="text-[11px]">{archivedRooms.length}</span>
          </button>

          {isArchiveOpen ? (
            <div className="mt-1 space-y-1">
              {archivedRooms.length ? (
                archivedRooms.map((room) => (
                  <RoomRow
                    archived
                    character={getCharacter(room.characterId)}
                    key={room.id}
                    room={room}
                    selected={room.id === selectedRoomId}
                    onDelete={() => confirmDelete(room.id)}
                    onRestore={() => onRestoreRoom(room.id)}
                    onSelect={() => onSelectRoom(room.id)}
                  />
                ))
              ) : (
                <p className="rounded-lg border border-dashed border-zeta-line px-3 py-4 text-center text-xs text-zeta-soft">
                  Archive is empty.
                </p>
              )}
            </div>
          ) : null}
        </section>
      </div>

      <section className="shrink-0 border-t border-zeta-line p-3">
        <div className="border-b border-zeta-line pb-3">
          <button
            aria-expanded={isMemoryOpen}
            className="flex w-full items-center justify-between gap-2 rounded-lg px-1 py-2 text-left transition hover:bg-zeta-panel2"
            onClick={() => setIsMemoryOpen((current) => !current)}
            type="button"
          >
            <span className="inline-flex items-center gap-2 text-xs font-semibold text-zeta-soft">
              {isMemoryOpen ? (
                <ChevronDown size={15} />
              ) : (
                <ChevronRight size={15} />
              )}
              Memory
            </span>
            <span className="text-[11px] text-zeta-soft">{memories.length}</span>
          </button>

          {isMemoryOpen ? (
            <div className="scrollbar-thin mt-2 max-h-36 space-y-2 overflow-y-auto">
              {memories.length ? (
                memories.slice(0, 12).map((memory) => (
                  <article
                    className="rounded-lg border border-zeta-line bg-zeta-panel2 p-2"
                    key={memory.id}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-xs font-semibold text-zeta-text">
                        {memory.chatTitle}
                      </p>
                      <time className="shrink-0 text-[10px] text-zeta-soft">
                        {formatMemoryDate(memory.recentCreatedAt)}
                      </time>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-zeta-muted">
                      {memory.summary}
                    </p>
                  </article>
                ))
              ) : (
                <p className="rounded-lg border border-dashed border-zeta-line px-3 py-4 text-center text-xs text-zeta-soft">
                  No saved memory yet.
                </p>
              )}
            </div>
          ) : null}
        </div>

        <div className="pt-3">
          {currentUser ? (
            <div className="mb-3 min-w-0 rounded-lg border border-zeta-line bg-zeta-panel2 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zeta-soft">
                Account
              </p>
              <p className="mt-1 truncate text-sm font-semibold text-zeta-text">
                {currentUser.name}
              </p>
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-2">
            <button
              aria-label="New chat"
              className="inline-flex h-10 min-w-0 items-center justify-center gap-2 rounded-lg bg-zeta-accent px-3 text-sm font-semibold text-zeta-buttonText transition hover:brightness-95"
              onClick={() => onNewChat()}
              type="button"
            >
              <MessageCirclePlus size={17} />
              <span className="truncate">새 채팅</span>
            </button>
            <button
              aria-label="Log out"
              className="inline-flex h-10 min-w-0 items-center justify-center gap-2 rounded-lg border border-zeta-line bg-zeta-panel px-3 text-sm font-semibold text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text disabled:cursor-not-allowed disabled:opacity-45"
              disabled={!currentUser || !onLogout}
              onClick={onLogout}
              type="button"
            >
              <LogOut size={17} />
              <span className="truncate">로그아웃</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function RoomRow({
  archived = false,
  character,
  room,
  selected,
  onArchive,
  onDelete,
  onRestore,
  onSelect,
}: {
  archived?: boolean;
  character: Character;
  room: ChatRoom;
  selected: boolean;
  onArchive?: () => void;
  onDelete: () => void;
  onRestore?: () => void;
  onSelect: () => void;
}) {
  return (
    <div
      className={cn(
        "group flex w-full items-center gap-2 rounded-lg px-3 py-3 transition",
        selected ? "bg-zeta-accentSoft" : "hover:bg-zeta-panel2",
      )}
    >
      <button
        className="flex min-w-0 flex-1 gap-3 text-left"
        onClick={onSelect}
        type="button"
      >
        <BotAvatar character={character} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center justify-between gap-3">
            <span className="truncate text-sm font-semibold text-zeta-text">
              {character.name}
            </span>
            <span className="shrink-0 text-[11px] text-zeta-soft">
              {room.lastMessageAt}
            </span>
          </span>
          <span className="mt-0.5 block truncate text-xs text-zeta-muted">
            {archived ? "[Archived] " : ""}
            {room.lastMessage}
          </span>
        </span>
      </button>

      <div className="flex shrink-0 items-center gap-1 opacity-100 md:opacity-0 md:transition md:group-hover:opacity-100 md:group-focus-within:opacity-100">
        {archived ? (
          <button
            aria-label="Restore chat"
            className="inline-flex size-8 items-center justify-center rounded-full text-zeta-soft transition hover:bg-zeta-panel hover:text-zeta-text"
            onClick={onRestore}
            title="Restore chat"
            type="button"
          >
            <ArchiveRestore size={15} />
          </button>
        ) : (
          <button
            aria-label="Archive chat"
            className="inline-flex size-8 items-center justify-center rounded-full text-zeta-soft transition hover:bg-zeta-panel hover:text-zeta-text"
            onClick={onArchive}
            title="Archive chat"
            type="button"
          >
            <Archive size={15} />
          </button>
        )}
        <button
          aria-label={archived ? "Delete archived chat" : "Delete chat"}
          className="inline-flex size-8 items-center justify-center rounded-full text-zeta-soft transition hover:bg-red-500/10 hover:text-red-400"
          onClick={onDelete}
          title={archived ? "Delete archived chat" : "Delete chat"}
          type="button"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
}

function formatMemoryDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
