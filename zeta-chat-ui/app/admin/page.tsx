"use client";

import { useEffect, useMemo, useState } from "react";
import {
  MessageSquare,
  Plus,
  RefreshCw,
  Save,
  Search,
  Trash2,
  UserRound,
} from "lucide-react";
import {
  AdminNavButton,
  Field,
  formatLogDate,
  getLogSessionSearchText,
  getVisiblePageNumbers,
  LogMetric,
  LogPagination,
  LogPreviewBlock,
  LogScopeButton,
  LogTimelineItem,
} from "@/components/admin/AdminWidgets";
import { cn } from "@/lib/utils";
import type {
  BotConfig,
  Character,
  ChatLogEntry,
  ChatLogSession,
  ChatModel,
  ChatModelsResult,
  ProviderSettings,
  RuntimeModel,
} from "@/types/chat";

type AdminSection = "chatbots" | "logs";

type AdminChatsResponse = {
  logs?: ChatLogEntry[];
  sessions?: ChatLogSession[];
  error?: string;
};

type AdminBotsResponse = Partial<BotConfig> & {
  path?: string;
  providerSettings?: Partial<ProviderSettings>;
  providerSettingsPath?: string;
  error?: string;
};

type CharacterDraft = Omit<Character, "tags"> & {
  tagsText: string;
};

const ADMIN_TOKEN_STORAGE_KEY = "zeta-admin-token";
const CHAT_LOG_PAGE_SIZE_OPTIONS = [10, 20, 30, 50, 100] as const;
const CHAT_LOG_FETCH_LIMIT = 1000;

function createCharacterDraft(modelId: string): CharacterDraft {
  const id = `bot-${Date.now()}`;
  return {
    id,
    name: "새 챗봇",
    avatar: "B",
    avatarImageUrl: "",
    coverGradient: "from-slate-500 via-zinc-500 to-neutral-500",
    intro: "챗봇 소개를 짧게 입력하세요.",
    tagsText: "기본",
    firstScene: "안녕하세요. 어떤 이야기를 해볼까요?",
    personaSummary: "",
    modelId,
  };
}

function toCharacterDraft(character: Character): CharacterDraft {
  return {
    ...character,
    avatarImageUrl: character.avatarImageUrl ?? "",
    tagsText: character.tags.join(", "),
  };
}

function fromCharacterDraft(draft: CharacterDraft): Character {
  return {
    id: draft.id.trim(),
    name: draft.name.trim(),
    avatar: draft.avatar.trim().slice(0, 2) || draft.name.trim().slice(0, 1),
    avatarImageUrl: draft.avatarImageUrl?.trim() || undefined,
    coverGradient: draft.coverGradient,
    intro: draft.intro.trim(),
    tags: draft.tagsText
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
    firstScene: draft.firstScene.trim(),
    personaSummary: draft.personaSummary.trim(),
    modelId: draft.modelId,
  };
}

function toModelId(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function runtimeModelToChatModel(model: RuntimeModel): ChatModel {
  return {
    id: toModelId(`${model.provider}-${model.apiName}`),
    label:
      model.provider === "openai"
        ? `OpenAI - ${model.label}`
        : model.provider === "deepseek"
          ? `DeepSeek - ${model.label}`
          : model.label,
    apiName: model.apiName,
    provider: model.provider,
    description:
      model.description ??
      (model.provider === "openai"
        ? "설정된 OpenAI 모델"
        : model.provider === "ollama"
          ? "Ollama에서 감지된 모델"
          : "LM Studio에서 감지된 모델"),
  };
}

function syncCharactersToModels(characters: Character[], models: ChatModel[]) {
  if (models.length === 0) {
    return characters;
  }

  const modelIds = new Set(models.map((model) => model.id));
  const fallbackModelId = models[0].id;

  return characters.map((character) =>
    modelIds.has(character.modelId)
      ? character
      : { ...character, modelId: fallbackModelId },
  );
}

async function fetchDetectedModels() {
  const response = await fetch("/api/models", { cache: "no-store" });
  const payload = (await response.json()) as ChatModelsResult;

  if (!response.ok || !Array.isArray(payload.models)) {
    throw new Error(payload.error ?? "서버 모델 목록을 불러오지 못했습니다.");
  }

  const configuredModels = payload.models.filter(
    (model) => model.source !== "fallback",
  );
  const runtimeModels = configuredModels.length ? configuredModels : payload.models;

  return {
    models: runtimeModels.map(runtimeModelToChatModel),
    error: payload.error ?? "",
    updatedAt: payload.updatedAt ?? "",
  };
}

async function fetchAdminLogs(adminToken: string) {
  const response = await fetch(`/api/admin/chats?limit=${CHAT_LOG_FETCH_LIMIT}`, {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  const payload = (await response.json()) as AdminChatsResponse;

  if (!response.ok) {
    throw new Error(payload.error ?? "대화 기록을 불러오지 못했습니다.");
  }

  return {
    logs: payload.logs ?? [],
    sessions: payload.sessions ?? [],
  };
}

export default function AdminPage() {
  const [activeSection, setActiveSection] = useState<AdminSection>("chatbots");
  const [token, setToken] = useState("");
  const [logs, setLogs] = useState<ChatLogEntry[]>([]);
  const [logSessions, setLogSessions] = useState<ChatLogSession[]>([]);
  const [models, setModels] = useState<ChatModel[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [defaultCharacterId, setDefaultCharacterId] = useState("");
  const [selectedCharacterId, setSelectedCharacterId] = useState("");
  const [characterDraft, setCharacterDraft] = useState<CharacterDraft | null>(
    null,
  );
  const [configPath, setConfigPath] = useState("");
  const [providerSettingsPath, setProviderSettingsPath] = useState("");
  const [deepseekApiKey, setDeepseekApiKey] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRefreshingLogs, setIsRefreshingLogs] = useState(false);
  const [isRefreshingModels, setIsRefreshingModels] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState("all");
  const [logUserSearch, setLogUserSearch] = useState("");
  const [chatLogPageSize, setChatLogPageSize] =
    useState<(typeof CHAT_LOG_PAGE_SIZE_OPTIONS)[number]>(30);
  const [chatLogPage, setChatLogPage] = useState(1);
  const logUserSearchQuery = logUserSearch.trim().toLowerCase();
  const selectedLogSession =
    selectedSessionId === "all"
      ? undefined
      : logSessions.find((session) => session.id === selectedSessionId);
  const visibleLogSessions = useMemo(() => {
    if (!logUserSearchQuery) {
      return logSessions;
    }

    return logSessions.filter((session) =>
      getLogSessionSearchText(session).includes(logUserSearchQuery),
    );
  }, [logSessions, logUserSearchQuery]);
  const visibleLogSessionIds = useMemo(
    () => new Set(visibleLogSessions.map((session) => session.id)),
    [visibleLogSessions],
  );

  const filteredLogs =
    selectedSessionId === "all"
      ? logUserSearchQuery
        ? logs.filter(
            (log) => log.sessionKey && visibleLogSessionIds.has(log.sessionKey),
          )
        : logs
      : logs.filter((log) => log.sessionKey === selectedSessionId);
  const totalLogErrors = logs.filter((log) => Boolean(log.error)).length;
  const selectedLogTitle =
    selectedLogSession?.name ??
    (logUserSearchQuery ? "검색된 사용자" : "모든 사용자");
  const selectedLogSubtitle = selectedLogSession
    ? `${selectedLogSession.chatTitles.length || selectedLogSession.chatIds.length}개 대화방, ${selectedLogSession.sessionIds.length}개 세션`
    : logUserSearchQuery
      ? `${visibleLogSessions.length}명 사용자 검색 결과`
      : "저장된 전체 기록";
  const chatLogPageCount = Math.max(
    1,
    Math.ceil(filteredLogs.length / chatLogPageSize),
  );
  const currentChatLogPage = Math.min(chatLogPage, chatLogPageCount);
  const pagedLogs = filteredLogs.slice(
    (currentChatLogPage - 1) * chatLogPageSize,
    currentChatLogPage * chatLogPageSize,
  );
  const logStartIndex =
    filteredLogs.length === 0
      ? 0
      : (currentChatLogPage - 1) * chatLogPageSize + 1;
  const logEndIndex = Math.min(
    currentChatLogPage * chatLogPageSize,
    filteredLogs.length,
  );
  const visibleChatLogPages = useMemo(
    () => getVisiblePageNumbers(currentChatLogPage, chatLogPageCount),
    [chatLogPageCount, currentChatLogPage],
  );
  const selectedCharacter = characters.find(
    (character) => character.id === selectedCharacterId,
  );

  const loadAdminData = async (tokenOverride = token) => {
    const adminToken = tokenOverride.trim();

    if (!adminToken) {
      setError("ADMIN_TOKEN을 입력하세요.");
      return;
    }

    setIsLoading(true);
    setError("");
    setNotice("");

    try {
      window.localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, adminToken);
      setToken(adminToken);
      const headers = { Authorization: `Bearer ${adminToken}` };
      const [botsResponse, chatLogsPayload, detectedModels] =
        await Promise.all([
          fetch("/api/admin/chatbots", { headers }),
          fetchAdminLogs(adminToken),
          fetchDetectedModels(),
        ]);

      const botsPayload = (await botsResponse.json()) as AdminBotsResponse;

      if (!botsResponse.ok) {
        throw new Error(
          botsPayload.error ?? "챗봇 설정을 불러오지 못했습니다.",
        );
      }

      const nextModels =
        detectedModels.models.length > 0
          ? detectedModels.models
          : botsPayload.models ?? [];
      const nextCharacters = syncCharactersToModels(
        botsPayload.characters ?? [],
        nextModels,
      );
      const nextCharacterId =
        selectedCharacterId &&
        nextCharacters.some((item) => item.id === selectedCharacterId)
          ? selectedCharacterId
          : botsPayload.defaultCharacterId ?? nextCharacters[0]?.id ?? "";
      const nextCharacter = nextCharacters.find(
        (item) => item.id === nextCharacterId,
      );
      setModels(nextModels);
      setCharacters(nextCharacters);
      setDefaultCharacterId(
        botsPayload.defaultCharacterId ?? nextCharacters[0]?.id ?? "",
      );
      setSelectedCharacterId(nextCharacterId);
      setCharacterDraft(nextCharacter ? toCharacterDraft(nextCharacter) : null);
      setConfigPath(botsPayload.path ?? "");
      setProviderSettingsPath(botsPayload.providerSettingsPath ?? "");
      setDeepseekApiKey(botsPayload.providerSettings?.deepseekApiKey ?? "");
      setLogs(chatLogsPayload.logs);
      setLogSessions(chatLogsPayload.sessions);
      setNotice("관리자 데이터를 불러왔습니다.");
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "관리자 데이터를 불러오지 못했습니다.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const savedToken = window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
    if (!savedToken) {
      return;
    }

    setToken(savedToken);
    void loadAdminData(savedToken);
    // Restore the remembered admin token once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setChatLogPage(1);
  }, [selectedSessionId, chatLogPageSize]);

  useEffect(() => {
    if (
      selectedSessionId !== "all" &&
      !logSessions.some((session) => session.id === selectedSessionId)
    ) {
      setSelectedSessionId("all");
    }
  }, [logSessions, selectedSessionId]);

  useEffect(() => {
    setChatLogPage((currentPage) => Math.min(currentPage, chatLogPageCount));
  }, [chatLogPageCount]);

  const refreshDetectedModelList = async () => {
    setIsRefreshingModels(true);
    setError("");
    setNotice("");

    try {
      const detectedModels = await fetchDetectedModels();
      const nextModels = detectedModels.models;
      const nextCharacters = syncCharactersToModels(characters, nextModels);
      const nextCharacter =
        nextCharacters.find((character) => character.id === selectedCharacterId) ??
        nextCharacters[0];

      setModels(nextModels);
      setCharacters(nextCharacters);
      setCharacterDraft(nextCharacter ? toCharacterDraft(nextCharacter) : null);
      setSelectedCharacterId(nextCharacter?.id ?? "");
      setNotice(
        detectedModels.error
          ? `모델 목록을 fallback으로 새로고침했습니다: ${detectedModels.error}`
          : "모델 목록을 새로고침했습니다.",
      );
    } catch (refreshError) {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "모델 목록을 새로고침하지 못했습니다.",
      );
    } finally {
      setIsRefreshingModels(false);
    }
  };

  const refreshLogs = async () => {
    const adminToken = token.trim();
    if (!adminToken) {
      setError("ADMIN_TOKEN을 입력하세요.");
      return;
    }

    setIsRefreshingLogs(true);
    setError("");
    setNotice("");

    try {
      const chatLogsPayload = await fetchAdminLogs(adminToken);
      setLogs(chatLogsPayload.logs);
      setLogSessions(chatLogsPayload.sessions);
      setNotice("대화 기록을 새로고침했습니다.");
    } catch (refreshError) {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "대화 기록을 새로고침하지 못했습니다.",
      );
    } finally {
      setIsRefreshingLogs(false);
    }
  };

  const saveConfig = async (
    nextModels: ChatModel[],
    nextCharacters: Character[],
    nextDefaultId = defaultCharacterId,
  ) => {
    setIsSaving(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch("/api/admin/chatbots", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token.trim()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          models: nextModels,
          characters: nextCharacters,
          defaultCharacterId: nextDefaultId || nextCharacters[0]?.id,
          providerSettings: {
            deepseekApiKey,
          },
        }),
      });
      const payload = (await response.json()) as AdminBotsResponse;

      if (!response.ok) {
        throw new Error(payload.error ?? "챗봇 설정을 저장하지 못했습니다.");
      }

      const savedModels = payload.models ?? nextModels;
      const savedCharacters = payload.characters ?? nextCharacters;
      const savedDefaultId = payload.defaultCharacterId ?? nextDefaultId;

      setModels(savedModels);
      setCharacters(savedCharacters);
      setDefaultCharacterId(savedDefaultId);
      setConfigPath(payload.path ?? configPath);
      setProviderSettingsPath(
        payload.providerSettingsPath ?? providerSettingsPath,
      );
      setDeepseekApiKey(
        payload.providerSettings?.deepseekApiKey ?? deepseekApiKey,
      );
      setNotice("챗봇 설정을 저장했습니다. 채팅 화면을 새로고침하면 적용됩니다.");

      return {
        models: savedModels,
        characters: savedCharacters,
        defaultCharacterId: savedDefaultId,
      };
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "챗봇 설정을 저장하지 못했습니다.",
      );
      return null;
    } finally {
      setIsSaving(false);
    }
  };

  const handleSelectCharacter = (character: Character) => {
    setSelectedCharacterId(character.id);
    setCharacterDraft(toCharacterDraft(character));
    setNotice("");
  };

  const handleNewCharacter = () => {
    const nextDraft = createCharacterDraft(models[0]?.id ?? "");
    setSelectedCharacterId(nextDraft.id);
    setCharacterDraft(nextDraft);
    setNotice("새 챗봇 초안을 작성한 뒤 저장하세요.");
  };

  const handleSaveCharacterDraft = async () => {
    if (!characterDraft) {
      return;
    }

    const nextCharacter = fromCharacterDraft(characterDraft);
    if (!nextCharacter.id || !nextCharacter.name || !nextCharacter.modelId) {
      setError("챗봇 ID, 이름, 모델은 필수입니다.");
      return;
    }

    if (!models.some((model) => model.id === nextCharacter.modelId)) {
      setError("감지된 서버 모델 중 하나를 선택하세요.");
      return;
    }

    const exists = characters.some(
      (character) => character.id === selectedCharacterId,
    );
    if (
      !exists &&
      characters.some((character) => character.id === nextCharacter.id)
    ) {
      setError("같은 ID의 챗봇이 이미 있습니다.");
      return;
    }

    const nextCharacters = exists
      ? characters.map((character) =>
          character.id === selectedCharacterId ? nextCharacter : character,
        )
      : [...characters, nextCharacter];
    const nextDefaultId = defaultCharacterId || nextCharacter.id;
    const saved = await saveConfig(models, nextCharacters, nextDefaultId);

    if (saved) {
      const savedCharacter =
        saved.characters.find((character) => character.id === nextCharacter.id) ??
        saved.characters[0];
      setSelectedCharacterId(savedCharacter.id);
      setCharacterDraft(toCharacterDraft(savedCharacter));
    }
  };

  const handleDeleteCharacter = async () => {
    if (!selectedCharacter || characters.length <= 1) {
      setError("챗봇은 최소 1개가 필요합니다.");
      return;
    }

    const nextCharacters = characters.filter(
      (character) => character.id !== selectedCharacter.id,
    );
    const nextDefaultId =
      defaultCharacterId === selectedCharacter.id
        ? nextCharacters[0].id
        : defaultCharacterId;
    const saved = await saveConfig(models, nextCharacters, nextDefaultId);

    if (saved) {
      setSelectedCharacterId(saved.characters[0].id);
      setCharacterDraft(toCharacterDraft(saved.characters[0]));
    }
  };

  const updateCharacterDraft = (field: keyof CharacterDraft, value: string) => {
    setCharacterDraft((current) =>
      current ? { ...current, [field]: value } : current,
    );
  };

  return (
    <main className="admin-page min-h-dvh bg-zeta-bg px-3 py-4 text-zeta-text sm:px-4 sm:py-6 md:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:gap-5">
        <header className="flex flex-col gap-3 border-b border-zeta-line pb-4 sm:gap-4 sm:pb-5">
          <div className="flex flex-col gap-2 sm:gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-zeta-soft">
                Zeta 관리자
              </p>
              <h1 className="mt-1 text-xl font-semibold sm:text-2xl">관리자 설정</h1>
              {configPath ? (
                <p className="mt-1 break-all text-xs text-zeta-muted">
                  설정 파일: {configPath}
                </p>
              ) : null}
            </div>
            <div className="flex gap-2">
              <input
                className="h-10 min-w-0 flex-1 rounded-lg border border-zeta-line bg-zeta-panel px-3 text-sm text-zeta-text outline-none placeholder:text-zeta-soft focus:border-zeta-accent sm:h-11 sm:w-80 sm:flex-none sm:px-4"
                onChange={(event) => setToken(event.target.value)}
                placeholder="ADMIN_TOKEN"
                type="password"
                value={token}
              />
              <button
                className="h-10 shrink-0 rounded-lg bg-zeta-accent px-4 text-sm font-semibold text-zeta-buttonText disabled:cursor-not-allowed disabled:opacity-50 sm:h-11 sm:px-5"
                disabled={!token.trim() || isLoading}
                onClick={() => loadAdminData()}
                type="button"
              >
                {isLoading ? "불러오는 중..." : "불러오기"}
              </button>
            </div>
          </div>

          <nav className="flex flex-wrap gap-2">
            <AdminNavButton
              active={activeSection === "chatbots"}
              label="챗봇"
              onClick={() => setActiveSection("chatbots")}
            />
            <AdminNavButton
              active={activeSection === "logs"}
              label="대화 기록"
              onClick={() => setActiveSection("logs")}
            />
          </nav>
        </header>

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : null}
        {notice ? (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700">
            {notice}
          </div>
        ) : null}

        {activeSection === "chatbots" ? (
          <section className="grid min-w-0 gap-3 sm:gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
            <aside className="min-w-0 overflow-hidden rounded-lg border border-zeta-line bg-zeta-panel p-2.5 sm:p-3">
              <div className="mb-2 flex items-center justify-between sm:mb-3">
                <h2 className="text-sm font-semibold">챗봇 목록</h2>
                <button
                  className="inline-flex items-center gap-1 rounded-lg bg-zeta-accent px-3 py-2 text-xs font-semibold text-zeta-buttonText disabled:opacity-50"
                  disabled={!models.length}
                  onClick={handleNewCharacter}
                  type="button"
                >
                  <Plus size={14} />
                  추가
                </button>
              </div>
              <div className="space-y-1">
                {characters.map((character) => (
                  <button
                    className={cn(
                      "w-full rounded-lg px-3 py-2 text-left text-sm",
                      character.id === selectedCharacterId
                        ? "bg-zeta-accentSoft text-zeta-text"
                        : "text-zeta-muted hover:bg-zeta-panel2",
                    )}
                    key={character.id}
                    onClick={() => handleSelectCharacter(character)}
                    type="button"
                  >
                    <span className="font-medium">{character.name}</span>
                    <span className="mt-0.5 block truncate text-xs text-zeta-soft">
                      {character.intro}
                    </span>
                  </button>
                ))}
              </div>
            </aside>

            <section className="min-w-0 overflow-hidden rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:p-4">
              <div className="mb-3 flex flex-col gap-2 border-b border-zeta-line pb-3 sm:mb-4 sm:gap-3 sm:pb-4 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <h2 className="text-base font-semibold sm:text-lg">챗봇 설정</h2>
                  <p className="mt-1 text-xs text-zeta-muted sm:text-sm">
                    모델은 설정된 provider endpoint에서 자동 감지됩니다.
                  </p>
                </div>
                <div className="flex min-w-0 gap-2">
                  <button
                    className="inline-flex h-10 items-center gap-2 rounded-lg border border-red-200 px-3 text-sm font-semibold text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={
                      !selectedCharacter || characters.length <= 1 || isSaving
                    }
                    onClick={handleDeleteCharacter}
                    type="button"
                  >
                    <Trash2 size={16} />
                    삭제
                  </button>
                  <button
                    className="inline-flex h-10 items-center gap-2 rounded-lg bg-zeta-accent px-4 text-sm font-semibold text-zeta-buttonText disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!characterDraft || isSaving || !models.length}
                    onClick={handleSaveCharacterDraft}
                    type="button"
                  >
                    <Save size={16} />
                    {isSaving ? "저장 중..." : "저장"}
                  </button>
                </div>
              </div>

              {characterDraft ? (
                <div className="grid min-w-0 gap-4 md:grid-cols-2">
                  <Field className="md:col-span-2" label="DeepSeek API Key">
                    <input
                      autoComplete="off"
                      className="input"
                      onChange={(event) => setDeepseekApiKey(event.target.value)}
                      placeholder="sk-..."
                      type="password"
                      value={deepseekApiKey}
                    />
                  </Field>
                  <Field label="챗봇 ID">
                    <input
                      className="input"
                      disabled={characters.some(
                        (character) => character.id === selectedCharacterId,
                      )}
                      onChange={(event) =>
                        updateCharacterDraft("id", event.target.value)
                      }
                      value={characterDraft.id}
                    />
                  </Field>
                  <Field label="이름">
                    <input
                      className="input"
                      onChange={(event) =>
                        updateCharacterDraft("name", event.target.value)
                      }
                      value={characterDraft.name}
                    />
                  </Field>
                  <Field label="기본 챗봇">
                    <select
                      className="input"
                      onChange={(event) => setDefaultCharacterId(event.target.value)}
                      value={defaultCharacterId}
                    >
                      {characters.map((character) => (
                        <option key={character.id} value={character.id}>
                          {character.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="모델">
                    <div className="flex gap-2">
                      <select
                        className="input min-w-0 flex-1"
                        disabled={!models.length}
                        onChange={(event) =>
                          updateCharacterDraft("modelId", event.target.value)
                        }
                        value={characterDraft.modelId}
                      >
                        {models.map((model) => (
                          <option key={model.id} value={model.id}>
                            {model.label}
                          </option>
                        ))}
                      </select>
                      <button
                        aria-label="모델 목록 새로고침"
                        className="inline-flex size-11 shrink-0 items-center justify-center rounded-lg bg-zeta-accent text-zeta-buttonText disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={isRefreshingModels || isLoading}
                        onClick={refreshDetectedModelList}
                        title="모델 목록 새로고침"
                        type="button"
                      >
                        <RefreshCw
                          className={
                            isRefreshingModels ? "animate-spin" : undefined
                          }
                          size={16}
                        />
                      </button>
                    </div>
                  </Field>
                  <Field label="아바타 글자">
                    <input
                      className="input"
                      maxLength={2}
                      onChange={(event) =>
                        updateCharacterDraft("avatar", event.target.value)
                      }
                      value={characterDraft.avatar}
                    />
                  </Field>
                  <Field label="프로필 이미지 URL">
                    <input
                      className="input"
                      onChange={(event) =>
                        updateCharacterDraft("avatarImageUrl", event.target.value)
                      }
                      placeholder="https://..."
                      value={characterDraft.avatarImageUrl ?? ""}
                    />
                  </Field>
                  <Field className="md:col-span-2" label="소개">
                    <textarea
                      className="textarea"
                      onChange={(event) =>
                        updateCharacterDraft("intro", event.target.value)
                      }
                      rows={3}
                      value={characterDraft.intro}
                    />
                  </Field>
                  <Field className="md:col-span-2" label="첫 메시지">
                    <textarea
                      className="textarea"
                      onChange={(event) =>
                        updateCharacterDraft("firstScene", event.target.value)
                      }
                      rows={3}
                      value={characterDraft.firstScene}
                    />
                  </Field>
                  <Field className="md:col-span-2" label="페르소나">
                    <textarea
                      className="textarea"
                      onChange={(event) =>
                        updateCharacterDraft(
                          "personaSummary",
                          event.target.value,
                        )
                      }
                      rows={7}
                      value={characterDraft.personaSummary}
                    />
                  </Field>
                  <Field className="md:col-span-2" label="태그">
                    <input
                      className="input"
                      onChange={(event) =>
                        updateCharacterDraft("tagsText", event.target.value)
                      }
                      placeholder="쉼표로 구분"
                      value={characterDraft.tagsText}
                    />
                  </Field>
                </div>
              ) : (
                <p className="text-sm text-zeta-muted">
                  ADMIN_TOKEN을 입력하고 관리자 데이터를 불러오세요.
                </p>
              )}
            </section>
          </section>
        ) : null}

        {activeSection === "logs" ? (
          <section className="space-y-3 rounded-lg border border-zeta-line bg-zeta-panel p-3 sm:space-y-4 sm:p-4">
            <div className="flex flex-col gap-2 sm:gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-base font-semibold sm:text-lg">저장된 대화 기록</h2>
                <p className="mt-1 text-xs text-zeta-muted sm:text-sm">
                  사용자를 고르면 해당 대화 흐름을 타임라인으로 확인합니다.
                </p>
              </div>
              <button
                className="inline-flex h-10 items-center justify-center gap-1.5 self-start rounded-lg bg-zeta-accent px-3 text-xs font-semibold text-zeta-buttonText disabled:cursor-not-allowed disabled:opacity-50 sm:gap-2 sm:px-4 sm:text-sm"
                disabled={!token.trim() || isRefreshingLogs}
                onClick={refreshLogs}
                type="button"
              >
                <RefreshCw
                  className={isRefreshingLogs ? "animate-spin" : undefined}
                  size={16}
                />
                기록 새로고침
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4">
              <LogMetric label="사용자" value={logSessions.length} />
              <LogMetric label="전체 기록" value={logs.length} />
              <LogMetric label="현재 표시" value={filteredLogs.length} />
              <LogMetric label="오류" value={totalLogErrors} />
            </div>

            <div className="grid gap-3 sm:gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
              <aside className="min-w-0 rounded-lg border border-zeta-line bg-zeta-panel2 p-2.5 sm:p-3 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:overflow-hidden">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-zeta-text">
                      사용자 목록
                    </h3>
                    <p className="mt-1 text-xs text-zeta-soft">
                      {visibleLogSessions.length} / {logSessions.length}명
                    </p>
                  </div>
                  <select
                    className="h-9 rounded-lg border border-zeta-line bg-zeta-panel px-2 text-xs text-zeta-text outline-none"
                    onChange={(event) =>
                      setChatLogPageSize(
                        Number(event.target.value) as typeof chatLogPageSize,
                      )
                    }
                    value={chatLogPageSize}
                  >
                    {CHAT_LOG_PAGE_SIZE_OPTIONS.map((pageSize) => (
                      <option key={pageSize} value={pageSize}>
                        {pageSize}개
                      </option>
                    ))}
                  </select>
                </div>

                <label className="relative mt-3 block min-w-0">
                  <span className="sr-only">로그 사용자 검색</span>
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zeta-soft"
                    size={16}
                  />
                  <input
                    className="h-10 w-full rounded-lg border border-zeta-line bg-zeta-panel py-2 pl-9 pr-3 text-sm text-zeta-text outline-none placeholder:text-zeta-soft"
                    onChange={(event) => setLogUserSearch(event.target.value)}
                    placeholder="이름, 대화방, 메시지 검색"
                    value={logUserSearch}
                  />
                </label>

                <div className="mt-2 space-y-2 sm:mt-3 xl:max-h-[calc(100vh-12rem)] xl:overflow-y-auto xl:pr-1">
                  <LogScopeButton
                    active={selectedSessionId === "all"}
                    icon={<MessageSquare size={16} />}
                    meta={`${filteredLogs.length}개 표시`}
                    onClick={() => setSelectedSessionId("all")}
                    subtitle={
                      logUserSearchQuery
                        ? "검색된 사용자 기록만 모아보기"
                        : "전체 기록을 최신순으로 모아보기"
                    }
                    title="모든 사용자"
                  />

                  {visibleLogSessions.map((session) => (
                    <LogScopeButton
                      active={selectedSessionId === session.id}
                      errorCount={session.errorCount}
                      icon={<UserRound size={16} />}
                      key={session.id}
                      meta={`기록 ${session.turnCount}개 · 최근 ${formatLogDate(
                        session.lastAt,
                      )}`}
                      onClick={() => setSelectedSessionId(session.id)}
                      subtitle={
                        session.chatTitles[0] ??
                        session.chatIds[0] ??
                        "대화방 정보 없음"
                      }
                      title={session.name}
                    />
                  ))}

                  {visibleLogSessions.length === 0 ? (
                    <p className="rounded-lg border border-zeta-line bg-zeta-panel p-4 text-sm text-zeta-muted">
                      {logUserSearchQuery
                        ? "검색어와 일치하는 사용자가 없습니다."
                        : "아직 저장된 사용자 기록이 없습니다."}
                    </p>
                  ) : null}
                </div>
              </aside>

              <div className="min-w-0 space-y-4">
                <div className="rounded-lg border border-zeta-line bg-zeta-panel2 p-3 sm:p-4">
                  <div className="flex flex-col gap-2 sm:gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase text-zeta-soft">
                        현재 보기
                      </p>
                      <h3 className="mt-1 truncate text-lg font-semibold text-zeta-text sm:text-xl">
                        {selectedLogTitle}
                      </h3>
                      <p className="mt-1 text-sm text-zeta-muted">
                        {selectedLogSubtitle}
                      </p>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <LogMetric label="표시" value={filteredLogs.length} />
                      <LogMetric
                        label="페이지"
                        value={currentChatLogPage}
                      />
                      <LogMetric label="전체 페이지" value={chatLogPageCount} />
                    </div>
                  </div>

                  {selectedLogSession ? (
                    <div className="mt-3 grid gap-2 sm:mt-4 sm:gap-3 md:grid-cols-2">
                      <LogPreviewBlock
                        label="최근 사용자 메시지"
                        text={
                          selectedLogSession.latestUserMessage ??
                          "최근 사용자 메시지가 없습니다."
                        }
                      />
                      <LogPreviewBlock
                        label="최근 응답"
                        text={
                          selectedLogSession.latestAssistantContent ??
                          "최근 응답이 없습니다."
                        }
                      />
                    </div>
                  ) : null}
                </div>

                {filteredLogs.length === 0 ? (
                  <p className="rounded-lg border border-zeta-line bg-zeta-panel2 p-4 text-sm text-zeta-muted">
                    현재 조건과 일치하는 대화 기록이 없습니다.
                  </p>
                ) : (
                  <>
                    <div className="flex flex-col gap-2 rounded-lg border border-zeta-line bg-zeta-panel2 p-2.5 sm:gap-3 sm:p-3 md:flex-row md:items-center md:justify-between">
                      <p className="text-xs text-zeta-muted sm:text-sm">
                        {filteredLogs.length}개 중 {logStartIndex}-{logEndIndex}
                        번째 기록
                      </p>
                      <LogPagination
                        currentPage={currentChatLogPage}
                        onPageChange={setChatLogPage}
                        pageCount={chatLogPageCount}
                        visiblePages={visibleChatLogPages}
                      />
                    </div>

                    <div className="space-y-2 sm:space-y-3">
                      {pagedLogs.map((log) => (
                        <LogTimelineItem key={log.id} log={log} />
                      ))}
                    </div>

                    <div className="flex flex-col gap-2 border-t border-zeta-line pt-3 sm:gap-3 sm:pt-4 md:flex-row md:items-center md:justify-between">
                      <p className="text-xs text-zeta-muted sm:text-sm">
                        {currentChatLogPage} / {chatLogPageCount}페이지
                      </p>
                      <LogPagination
                        currentPage={currentChatLogPage}
                        onPageChange={setChatLogPage}
                        pageCount={chatLogPageCount}
                        visiblePages={visibleChatLogPages}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
