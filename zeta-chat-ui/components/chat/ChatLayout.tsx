"use client";

import type { CSSProperties } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PanelLeftOpen, X } from "lucide-react";
import { sendMessage } from "@/lib/chat-api";
import {
  characters as fallbackCharacters,
  chatRooms as fallbackRooms,
} from "@/lib/mock-data";
import {
  DEFAULT_RESPONSE_STYLE,
  normalizeResponseStyle,
} from "@/lib/response-formats";
import type {
  AccountChatState,
  AuthUser,
  BotConfig,
  Character,
  ChatRoom,
  MemoryItem,
  Message,
  ResponseStyle,
} from "@/types/chat";
import { AccountSettingsDialog } from "./AccountSettingsDialog";
import { AuthPanel } from "./AuthPanel";
import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { ChatSidebar } from "./ChatSidebar";
import { CustomPromptDialog } from "./CustomPromptDialog";
import { MessageList } from "./MessageList";
import { MobileNav } from "./MobileNav";
import { HomeDiscover } from "./HomeDiscover";

type MobilePanel = "rooms" | null;
type AppView = "home" | "chat";

const ADMIN_VISIBLE_ACCOUNT_NAME = "yeonnu";

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}`;
}

function nowLabel() {
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date());
}

function createRoom(character: Character): ChatRoom {
  return {
    id: createId("room"),
    characterId: character.id,
    title: `${character.name} 대화`,
    lastMessage: character.firstScene,
    lastMessageAt: "방금",
    messages: [
      {
        id: createId("message"),
        role: "assistant",
        content: character.firstScene,
        createdAt: nowLabel(),
      },
    ],
  };
}

function getCharacterForRoom(room: ChatRoom, allCharacters: Character[]) {
  return allCharacters.find((character) => character.id === room.characterId);
}

function ensureOpeningMessage(room: ChatRoom, character: Character): ChatRoom {
  if (room.messages.length > 0) {
    return room;
  }

  const openingMessage: Message = {
    id: createId("message"),
    role: "assistant",
    content: character.firstScene,
    createdAt: nowLabel(),
  };

  return {
    ...room,
    lastMessage: room.lastMessage || character.firstScene,
    lastMessageAt: room.lastMessageAt || openingMessage.createdAt,
    messages: [openingMessage],
  };
}

function withRoomMessages(
  room: ChatRoom,
  messages: Message[],
  lastMessage?: string,
): ChatRoom {
  return {
    ...room,
    messages,
    lastMessage: lastMessage ?? messages.at(-1)?.content ?? room.lastMessage,
    lastMessageAt: nowLabel(),
  };
}

function createMessageDisplayQueue({
  onToken,
  signal,
}: {
  onToken: (token: string) => void;
  signal: AbortSignal;
}) {
  let displayedContent = "";

  return {
    push(token: string) {
      if (!token || signal.aborted) {
        return;
      }

      displayedContent += token;
      onToken(token);
    },
    finish() {
      return Promise.resolve(displayedContent);
    },
    cancel() {
      return displayedContent;
    },
    getDisplayedContent() {
      return displayedContent;
    },
  };
}

function isStoppedGeneration(signal: AbortSignal) {
  return signal.aborted;
}

function normalizeRoomsForCharacters(
  currentRooms: ChatRoom[],
  allCharacters: Character[],
  defaultCharacterId?: string,
) {
  const availableRooms = currentRooms.flatMap((room) => {
    const character = getCharacterForRoom(room, allCharacters);
    return character ? [ensureOpeningMessage(room, character)] : [];
  });

  if (availableRooms.length > 0) {
    return availableRooms;
  }

  const defaultCharacter =
    allCharacters.find((character) => character.id === defaultCharacterId) ??
    allCharacters[0];

  return defaultCharacter ? [createRoom(defaultCharacter)] : [];
}

export function ChatLayout() {
  const [characters, setCharacters] = useState<Character[]>(fallbackCharacters);
  const [rooms, setRooms] = useState<ChatRoom[]>(() =>
    normalizeRoomsForCharacters(fallbackRooms, fallbackCharacters),
  );
  const [selectedRoomId, setSelectedRoomId] = useState(fallbackRooms[0].id);
  const [isSending, setIsSending] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>(null);
  const [isCustomPromptOpen, setIsCustomPromptOpen] = useState(false);
  const [isAccountSettingsOpen, setIsAccountSettingsOpen] = useState(false);
  const [customPromptDraft, setCustomPromptDraft] = useState("");
  const [customPromptAppendDraft, setCustomPromptAppendDraft] = useState("");
  const [sessionId] = useState(() => {
    if (typeof window === "undefined") {
      return createId("session");
    }

    const saved = window.localStorage.getItem("zeta-session-id");
    if (saved) {
      return saved;
    }

    const nextSessionId = createId("session");
    window.localStorage.setItem("zeta-session-id", nextSessionId);
    return nextSessionId;
  });
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [responseStyle, setResponseStyle] = useState<ResponseStyle>(
    DEFAULT_RESPONSE_STYLE,
  );
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(true);
  const [activeView, setActiveView] = useState<AppView>("chat");
  const abortControllerRef = useRef<AbortController | null>(null);
  const appName = process.env.NEXT_PUBLIC_APP_NAME ?? "Zeta";

  const persistRoom = useCallback(
    (room: ChatRoom) => {
      if (!currentUser) {
        return;
      }

      const savedRoom: ChatRoom = {
        ...room,
        messages: room.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          createdAt: message.createdAt,
        })),
      };

      void fetch("/api/account/rooms", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ room: savedRoom }),
      }).catch(() => undefined);
    },
    [currentUser],
  );

  const deletePersistedRoom = useCallback(
    (roomId: string) => {
      if (!currentUser) {
        return;
      }

      void fetch(`/api/account/rooms?roomId=${encodeURIComponent(roomId)}`, {
        method: "DELETE",
      }).catch(() => undefined);
    },
    [currentUser],
  );

  const replaceRoom = useCallback((nextRoom: ChatRoom) => {
    setRooms((currentRooms) =>
      currentRooms.map((room) => (room.id === nextRoom.id ? nextRoom : room)),
    );
  }, []);

  const applyAccountState = (
    user: AuthUser,
    state?: AccountChatState,
    characterList = characters,
  ) => {
    const nextRooms = normalizeRoomsForCharacters(
      state?.rooms ?? [],
      characterList,
    );

    setCurrentUser(user);
    setMemories(state?.memories ?? []);
    setResponseStyle(normalizeResponseStyle(state?.responseStyle));
    setRooms(nextRooms);
    if (nextRooms[0]) {
      setSelectedRoomId(nextRooms[0].id);
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        const response = await fetch("/api/auth/session", {
          cache: "no-store",
        });
        const payload = (await response.json().catch(() => null)) as {
          user: AuthUser | null;
          state: AccountChatState;
        } | null;

        if (cancelled) {
          return;
        }

        if (payload?.user) {
          applyAccountState(payload.user, payload.state);
        } else {
          setCurrentUser(null);
          setMemories([]);
          setResponseStyle(DEFAULT_RESPONSE_STYLE);
        }
      } catch {
        if (!cancelled) {
          setCurrentUser(null);
          setMemories([]);
          setResponseStyle(DEFAULT_RESPONSE_STYLE);
        }
      } finally {
        if (!cancelled) {
          setIsAuthLoading(false);
        }
      }
    }

    loadSession();
    return () => {
      cancelled = true;
    };
    // The session should be restored once on mount; later character updates
    // normalize the already-loaded rooms separately.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadChatbots() {
      const response = await fetch("/api/chatbots", { cache: "no-store" });
      if (!response.ok) {
        return;
      }

      const config = (await response.json()) as BotConfig;
      if (cancelled || !config.characters?.length) {
        return;
      }

      setCharacters(config.characters);
      setRooms((currentRooms) => {
        return normalizeRoomsForCharacters(
          currentRooms,
          config.characters,
          config.defaultCharacterId,
        );
      });
    }

    loadChatbots().catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const selectedRoom = useMemo(
    () => rooms.find((room) => room.id === selectedRoomId) ?? rooms[0],
    [rooms, selectedRoomId],
  );

  const selectedCharacter =
    characters.find(
      (character) => character.id === selectedRoom?.characterId,
    ) ?? characters[0];

  useEffect(() => {
    if (rooms.length > 0 && !rooms.some((room) => room.id === selectedRoomId)) {
      setSelectedRoomId(rooms[0].id);
    }
  }, [rooms, selectedRoomId]);

  useEffect(() => {
    if (!selectedRoom && characters[0]) {
      const room = createRoom(characters[0]);
      setRooms([room]);
      setSelectedRoomId(room.id);
      return;
    }

    if (
      selectedRoom &&
      !characters.some((item) => item.id === selectedRoom.characterId)
    ) {
      const room = createRoom(characters[0]);
      setRooms((currentRooms) => [room, ...currentRooms]);
      setSelectedRoomId(room.id);
      return;
    }

    if (
      selectedRoom &&
      selectedCharacter &&
      selectedRoom.messages.length === 0
    ) {
      setRooms((currentRooms) =>
        currentRooms.map((room) =>
          room.id === selectedRoom.id
            ? ensureOpeningMessage(room, selectedCharacter)
            : room,
        ),
      );
    }
  }, [characters, selectedCharacter, selectedRoom]);

  const updateRoomMessages = (
    roomId: string,
    updater: (messages: Message[]) => Message[],
    lastMessage?: string,
  ) => {
    setRooms((currentRooms) =>
      currentRooms.map((room) => {
        if (room.id !== roomId) {
          return room;
        }

        const messages = updater(room.messages);
        return {
          ...room,
          messages,
          lastMessage:
            lastMessage ?? messages.at(-1)?.content ?? room.lastMessage,
          lastMessageAt: nowLabel(),
        };
      }),
    );
  };

  const appendStreamingToken = (
    roomId: string,
    messageId: string,
    token: string,
  ) => {
    if (!token) {
      return;
    }

    updateRoomMessages(roomId, (messages) =>
      messages.map((message) =>
        message.id === messageId
          ? { ...message, content: `${message.content}${token}` }
          : message,
      ),
    );
  };

  const generateAssistantReply = async ({
    assistantCreatedAt,
    assistantMessageId,
    character,
    content,
    messages,
    room,
    turnAction,
  }: {
    assistantCreatedAt: string;
    assistantMessageId: string;
    character: Character;
    content: string;
    messages: Message[];
    room: ChatRoom;
    turnAction?: "message" | "skip";
  }) => {
    setIsSending(true);
    const abortController = new AbortController();
    const displayQueue = createMessageDisplayQueue({
      signal: abortController.signal,
      onToken: (token) => {
        appendStreamingToken(room.id, assistantMessageId, token);
      },
    });
    abortControllerRef.current = abortController;

    try {
      const result = await sendMessage({
        chatId: room.id,
        sessionId,
        chatTitle: room.title,
        character,
        customCharacterPrompt: room.customCharacterPrompt,
        messages,
        content,
        responseStyle,
        turnAction,
        signal: abortController.signal,
        onToken: (token) => {
          displayQueue.push(token);
        },
      });
      await displayQueue.finish();

      const assistantMessage: Message = {
        id: assistantMessageId,
        role: "assistant",
        content: result.content,
        createdAt: assistantCreatedAt,
      };
      const finalRoom = withRoomMessages(
        room,
        [...messages, assistantMessage],
        result.content,
      );
      replaceRoom(finalRoom);
      persistRoom(finalRoom);

      if (result.memoryItem) {
        setMemories((currentMemories) => [
          result.memoryItem!,
          ...currentMemories,
        ]);
      }
    } catch (error) {
      const displayedContent = displayQueue.cancel();
      if (isStoppedGeneration(abortController.signal)) {
        const stoppedMessages = displayedContent.trim()
          ? [
              ...messages,
              {
                id: assistantMessageId,
                role: "assistant" as const,
                content: displayedContent,
                createdAt: assistantCreatedAt,
              },
            ]
          : messages;
        const stoppedRoom = withRoomMessages(
          room,
          stoppedMessages,
          displayedContent.trim() ? displayedContent : room.lastMessage,
        );
        replaceRoom(stoppedRoom);
        persistRoom(stoppedRoom);
        return;
      }

      const errorText =
        error instanceof Error
          ? error.message
          : "Chat response generation failed.";
      const contentPrefix = displayedContent.trim()
        ? `${displayedContent}\n\n`
        : "";
      const failedContent = `${contentPrefix}Response generation failed. Please retry. ${errorText}`;
      const failedRoom = withRoomMessages(
        room,
        [
          ...messages,
          {
            id: assistantMessageId,
            role: "assistant",
            content: failedContent,
            createdAt: assistantCreatedAt,
          },
        ],
        failedContent,
      );
      replaceRoom(failedRoom);
      persistRoom(failedRoom);
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
      setIsSending(false);
    }
  };

  const handleAbortGeneration = () => {
    abortControllerRef.current?.abort();
  };

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    const fallback = normalizeRoomsForCharacters(fallbackRooms, characters);
    setCurrentUser(null);
    setMemories([]);
    setResponseStyle(DEFAULT_RESPONSE_STYLE);
    setRooms(fallback);
    setIsAccountSettingsOpen(false);
    setMobilePanel(null);
    if (fallback[0]) {
      setSelectedRoomId(fallback[0].id);
    }
  };

  const handleAuthenticated = (user: AuthUser, state?: AccountChatState) => {
    applyAccountState(user, state);
  };

  const handleSelectRoom = (roomId: string) => {
    setSelectedRoomId(roomId);
    setMobilePanel(null);
  };

  const handleNewChat = (characterId = selectedCharacter.id) => {
    const character =
      characters.find((item) => item.id === characterId) ?? selectedCharacter;
    const newRoom = createRoom(character);

    setRooms((currentRooms) => [newRoom, ...currentRooms]);
    setSelectedRoomId(newRoom.id);
    persistRoom(newRoom);
    setMobilePanel(null);
    setActiveView("chat");
  };

  const handleArchiveRoom = (roomId: string) => {
    const room = rooms.find((item) => item.id === roomId);
    if (!room) {
      return;
    }

    const archivedRoom: ChatRoom = {
      ...room,
      archivedAt: new Date().toISOString(),
    };
    let nextRooms = rooms.map((item) =>
      item.id === roomId ? archivedRoom : item,
    );
    const activeRooms = nextRooms.filter((item) => !item.archivedAt);
    let nextSelectedRoomId = selectedRoomId;

    if (selectedRoomId === roomId) {
      if (activeRooms[0]) {
        nextSelectedRoomId = activeRooms[0].id;
      } else if (selectedCharacter) {
        const newRoom = createRoom(selectedCharacter);
        nextRooms = [newRoom, ...nextRooms];
        nextSelectedRoomId = newRoom.id;
        persistRoom(newRoom);
      }
    }

    setRooms(nextRooms);
    setSelectedRoomId(nextSelectedRoomId);
    persistRoom(archivedRoom);
  };

  const handleRestoreRoom = (roomId: string) => {
    const room = rooms.find((item) => item.id === roomId);
    if (!room) {
      return;
    }

    const restoredRoom: ChatRoom = {
      ...room,
      archivedAt: undefined,
      lastMessageAt: nowLabel(),
    };
    setRooms((currentRooms) =>
      currentRooms.map((item) => (item.id === roomId ? restoredRoom : item)),
    );
    setSelectedRoomId(roomId);
    persistRoom(restoredRoom);
  };

  const handleDeleteRoom = (roomId: string) => {
    let nextRooms = rooms.filter((room) => room.id !== roomId);
    let nextSelectedRoomId = selectedRoomId;

    if (selectedRoomId === roomId) {
      const nextActiveRoom = nextRooms.find((room) => !room.archivedAt);
      const nextRoom = nextActiveRoom ?? nextRooms[0];

      if (nextRoom) {
        nextSelectedRoomId = nextRoom.id;
      } else if (selectedCharacter) {
        const newRoom = createRoom(selectedCharacter);
        nextRooms = [newRoom];
        nextSelectedRoomId = newRoom.id;
        persistRoom(newRoom);
      }
    }

    setRooms(nextRooms);
    setSelectedRoomId(nextSelectedRoomId);
    deletePersistedRoom(roomId);
    setMobilePanel(null);
  };

  const handleSend = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || isSending || !selectedRoom || !selectedCharacter) {
      return;
    }

    const userMessage: Message = {
      id: createId("message"),
      role: "user",
      content: trimmed,
      createdAt: nowLabel(),
    };

    const nextMessages = [...selectedRoom.messages, userMessage];
    const roomAfterUserMessage = withRoomMessages(
      selectedRoom,
      nextMessages,
      trimmed,
    );
    replaceRoom(roomAfterUserMessage);
    persistRoom(roomAfterUserMessage);

    const assistantMessageId = createId("message");
    const assistantCreatedAt = nowLabel();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      createdAt: assistantCreatedAt,
      isStreaming: true,
    };
    replaceRoom(
      withRoomMessages(
        roomAfterUserMessage,
        [...nextMessages, assistantMessage],
        trimmed,
      ),
    );

    await generateAssistantReply({
      assistantCreatedAt,
      assistantMessageId,
      character: selectedCharacter,
      content: trimmed,
      messages: nextMessages,
      room: roomAfterUserMessage,
    });
  };

  const handleSkipTurn = async () => {
    if (
      isSending ||
      !selectedRoom ||
      !selectedCharacter ||
      selectedRoom.messages.at(-1)?.role !== "assistant"
    ) {
      return;
    }

    const assistantMessageId = createId("message");
    const assistantCreatedAt = nowLabel();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      createdAt: assistantCreatedAt,
      isStreaming: true,
    };
    replaceRoom(
      withRoomMessages(
        selectedRoom,
        [...selectedRoom.messages, assistantMessage],
        selectedRoom.lastMessage,
      ),
    );

    await generateAssistantReply({
      assistantCreatedAt,
      assistantMessageId,
      character: selectedCharacter,
      content: "",
      messages: selectedRoom.messages,
      room: selectedRoom,
      turnAction: "skip",
    });
  };

  const handleOpenCustomPrompt = () => {
    if (!selectedRoom) {
      return;
    }

    setCustomPromptDraft(selectedRoom.customCharacterPrompt ?? "");
    setCustomPromptAppendDraft("");
    setIsCustomPromptOpen(true);
  };

  const persistCustomPrompt = (nextPrompt: string) => {
    if (!selectedRoom) {
      return;
    }

    const nextRoom: ChatRoom = {
      ...selectedRoom,
      customCharacterPrompt: nextPrompt || undefined,
    };

    replaceRoom(nextRoom);
    persistRoom(nextRoom);
    setCustomPromptDraft(nextPrompt);
  };

  const handleAppendCustomPrompt = () => {
    if (!customPromptAppendDraft) {
      return;
    }

    const nextPrompt = customPromptDraft
      ? `${customPromptDraft}\n${customPromptAppendDraft}`
      : customPromptAppendDraft;

    persistCustomPrompt(nextPrompt);
    setCustomPromptAppendDraft("");
  };

  const handleDeleteMessage = (messageId: string) => {
    if (!selectedRoom) {
      return;
    }

    const nextMessages = selectedRoom.messages.filter(
      (message) => message.id !== messageId,
    );
    const nextRoom = withRoomMessages(selectedRoom, nextMessages);
    replaceRoom(nextRoom);
    persistRoom(nextRoom);
  };

  const handleEditMessage = (messageId: string, content: string) => {
    if (!selectedRoom) {
      return;
    }

    const nextMessages = selectedRoom.messages.map((message) =>
      message.id === messageId ? { ...message, content } : message,
    );
    const nextRoom = withRoomMessages(selectedRoom, nextMessages);
    replaceRoom(nextRoom);
    persistRoom(nextRoom);
  };

  const handleRegenerateMessage = async (messageId: string) => {
    if (isSending || !selectedRoom || !selectedCharacter) {
      return;
    }

    const messageIndex = selectedRoom.messages.findIndex(
      (message) => message.id === messageId && message.role === "assistant",
    );
    if (messageIndex <= 0) {
      return;
    }

    const baseMessages = selectedRoom.messages.slice(0, messageIndex);
    const previousUserMessage = baseMessages
      .slice()
      .reverse()
      .find((message) => message.role === "user");
    if (!previousUserMessage) {
      return;
    }

    const assistantCreatedAt = nowLabel();
    const assistantMessage: Message = {
      id: messageId,
      role: "assistant",
      content: "",
      createdAt: assistantCreatedAt,
      isStreaming: true,
    };
    const baseRoom = withRoomMessages(
      selectedRoom,
      baseMessages,
      previousUserMessage.content,
    );
    replaceRoom(
      withRoomMessages(
        baseRoom,
        [...baseMessages, assistantMessage],
        previousUserMessage.content,
      ),
    );

    await generateAssistantReply({
      assistantCreatedAt,
      assistantMessageId: messageId,
      character: selectedCharacter,
      content: previousUserMessage.content,
      messages: baseMessages,
      room: baseRoom,
    });
  };

  if (isAuthLoading) {
    return (
      <main className="grid min-h-dvh place-items-center bg-zeta-bg text-sm text-zeta-muted">
        챗봇을 불러오는 중입니다.
      </main>
    );
  }

  if (!currentUser) {
    return (
      <AuthPanel appName={appName} onAuthenticated={handleAuthenticated} />
    );
  }

  if (activeView === "home") {
    return (
      <>
        <HomeDiscover
          characters={characters}
          onOpenChat={(characterId) => handleNewChat(characterId)}
          onOpenProfile={() => setIsAccountSettingsOpen(true)}
          onViewChange={setActiveView}
        />
        {isAccountSettingsOpen ? (
          <AccountSettingsDialog
            memories={memories}
            user={currentUser}
            onClose={() => setIsAccountSettingsOpen(false)}
            onLogout={handleLogout}
            onUserChange={setCurrentUser}
          />
        ) : null}
      </>
    );
  }

  if (!selectedRoom || !selectedCharacter) {
    return (
      <main className="grid min-h-dvh place-items-center bg-zeta-bg text-sm text-zeta-muted">
        대화를 준비하는 중입니다.
      </main>
    );
  }

  const canSkipTurn = selectedRoom.messages.at(-1)?.role === "assistant";
  const showAdminLink =
    currentUser.name.trim().toLocaleLowerCase("en-US") ===
    ADMIN_VISIBLE_ACCOUNT_NAME;

  const sidebar = (
    <ChatSidebar
      appName={appName}
      characters={characters}
      currentUser={currentUser ?? undefined}
      memories={memories}
      rooms={rooms}
      selectedRoomId={selectedRoom.id}
      onArchiveRoom={handleArchiveRoom}
      onDeleteRoom={handleDeleteRoom}
      onLogout={handleLogout}
      onCollapse={mobilePanel ? undefined : () => setIsLeftCollapsed(true)}
      onNewChat={handleNewChat}
      onRestoreRoom={handleRestoreRoom}
      onSelectRoom={handleSelectRoom}
    />
  );

  const layoutStyle = {
    "--left-sidebar-width": isLeftCollapsed ? "64px" : "280px",
  } as CSSProperties;

  return (
    <main className="h-dvh overflow-hidden bg-zeta-bg text-zeta-text">
      <div
        className="grid h-full min-h-0 grid-cols-1 md:[grid-template-columns:var(--left-sidebar-width)_minmax(0,1fr)]"
        style={layoutStyle}
      >
        <aside className="hidden min-h-0 min-w-0 overflow-hidden border-r border-zeta-line bg-zeta-panel md:block">
          {isLeftCollapsed ? (
            <CollapsedPanelButton
              label="Expand chat list"
              onClick={() => setIsLeftCollapsed(false)}
            />
          ) : (
            sidebar
          )}
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col overflow-hidden bg-zeta-bg">
          <MobileNav
            character={selectedCharacter}
            hasCustomCharacterPrompt={Boolean(
              selectedRoom.customCharacterPrompt?.trim(),
            )}
            room={selectedRoom}
            onEditCustomCharacterPrompt={handleOpenCustomPrompt}
            onOpenHome={() => setActiveView("home")}
            onOpenAccountSettings={() => setIsAccountSettingsOpen(true)}
            onOpenRooms={() => setMobilePanel("rooms")}
          />
          <ChatHeader
            character={selectedCharacter}
            hasCustomCharacterPrompt={Boolean(
              selectedRoom.customCharacterPrompt?.trim(),
            )}
            room={selectedRoom}
            showAdminLink={showAdminLink}
            onEditCustomCharacterPrompt={handleOpenCustomPrompt}
            onOpenHome={() => setActiveView("home")}
            onOpenAccountSettings={() => setIsAccountSettingsOpen(true)}
          />
          <MessageList
            character={selectedCharacter}
            messages={selectedRoom.messages}
            isSending={isSending}
            onDelete={handleDeleteMessage}
            onEdit={handleEditMessage}
            onOpenCharacterSettings={handleOpenCustomPrompt}
            onRegenerate={handleRegenerateMessage}
          />
          <ChatInput
            canSkipTurn={canSkipTurn}
            isSending={isSending}
            onAbort={handleAbortGeneration}
            onSend={handleSend}
            onSkipTurn={handleSkipTurn}
            character={selectedCharacter}
            messages={selectedRoom.messages}
          />
        </section>
      </div>

      {mobilePanel ? (
        <div className="fixed inset-0 z-50 bg-black/35 md:hidden">
          <button
            aria-label="닫기"
            className="absolute right-4 top-4 z-10 rounded-full border border-zeta-line bg-zeta-panel p-2 text-zeta-muted shadow-zeta"
            onClick={() => setMobilePanel(null)}
            type="button"
          >
            <X size={18} />
          </button>
          <div className="h-full w-[min(88vw,24rem)] max-w-full overflow-hidden border-r border-zeta-line bg-zeta-panel shadow-zeta">
            {sidebar}
          </div>
        </div>
      ) : null}

      {isCustomPromptOpen ? (
        <CustomPromptDialog
          appendDraft={customPromptAppendDraft}
          savedDraft={customPromptDraft}
          onCancel={() => setIsCustomPromptOpen(false)}
          onAppendChange={setCustomPromptAppendDraft}
          onAppendSave={handleAppendCustomPrompt}
          onClearAppend={() => setCustomPromptAppendDraft("")}
        />
      ) : null}

      {isAccountSettingsOpen ? (
        <AccountSettingsDialog
          memories={memories}
          user={currentUser}
          onClose={() => setIsAccountSettingsOpen(false)}
          onLogout={handleLogout}
          onUserChange={setCurrentUser}
        />
      ) : null}
    </main>
  );
}

function CollapsedPanelButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <div className="flex h-full flex-col items-center gap-3 px-2 py-4">
      <button
        aria-label={label}
        className="inline-flex size-10 items-center justify-center rounded-full border border-zeta-line bg-zeta-panel text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
        onClick={onClick}
        title={label}
        type="button"
      >
        <PanelLeftOpen size={18} />
      </button>
    </div>
  );
}
