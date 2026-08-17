import { appendFile, mkdir, open, stat } from "fs/promises";
import path from "path";
import {
  getDataPath,
  isNotFoundError,
  readJsonFile,
  sanitizePathSegment,
  withFileLock,
  writeTextFile,
  writeJsonFile,
} from "@/lib/server-files";
import { rankMemoryDocuments } from "@/lib/chat-memory-ranking";
import type { Character, Message } from "@/types/chat";

export {
  buildMemoryUpdatePrompt,
  parseMemoryUpdate,
} from "@/lib/chat-memory-extraction";

type MemoryProfile = Record<string, string>;

type MemoryRelationship = {
  intimacy: number;
  trust: number;
  mood: string;
  dynamic: string;
  openLoops: string[];
  boundaries: string[];
  lastInteractionAt?: string;
};

type MemoryEvent = {
  id: string;
  title: string;
  description: string;
  emotion?: string;
  importance: number;
  createdAt: string;
};

type MemoryEdge = {
  subject: string;
  relation: string;
  object: string;
};

type MemoryDocumentKind =
  "turn" | "event" | "summary" | "profile" | "preference" | "relationship";

type MemoryDocument = {
  id: string;
  kind: MemoryDocumentKind;
  text: string;
  importance: number;
  createdAt: string;
};

export type ChatMemoryState = {
  version: 1;
  sessionId: string;
  chatId: string;
  characterId: string;
  updatedAt: string;
  turnCount: number;
  summary: string;
  profile: MemoryProfile;
  preferences: MemoryProfile;
  relationship: MemoryRelationship;
  events: MemoryEvent[];
  graph: MemoryEdge[];
  chunks: MemoryDocument[];
};

export type MemoryUpdate = {
  summary?: string;
  profile?: MemoryProfile;
  preferences?: MemoryProfile;
  relationship?: Partial<MemoryRelationship>;
  events?: Array<{
    title?: string;
    description?: string;
    emotion?: string;
    importance?: number;
  }>;
  graph?: Array<{
    subject?: string;
    relation?: string;
    object?: string;
  }>;
  documents?: Array<{
    kind?: MemoryDocumentKind;
    text?: string;
    importance?: number;
  }>;
};

export type MemoryTurn = {
  userContent: string;
  assistantContent: string;
  messages: Message[];
};

const MEMORY_DIR_NAME = "memory";
const STATE_FILE_NAME = "state.json";
const RELATIONSHIP_FILE_NAME = "relationship.json";
const DOCUMENTS_FILE_NAME = "documents.jsonl";
const TURNS_FILE_NAME = "turns.jsonl";
const MAX_SUMMARY_CHARS = 5000;
const MAX_EVENTS = 80;
const MAX_GRAPH_EDGES = 120;
const MAX_CHUNKS = 40;
const DEFAULT_MEMORY_RAG_TOP_K = 3;
const DEFAULT_MEMORY_RECENT_EVENTS = 4;
const DEFAULT_MEMORY_CONTEXT_CHUNKS = 3;
const DEFAULT_MEMORY_CONTEXT_GRAPH_EDGES = 12;
const DEFAULT_MEMORY_CONTEXT_SUMMARY_CHARS = 500;
const DEFAULT_MEMORY_CONTEXT_ITEM_CHARS = 500;
const DEFAULT_MEMORY_CONTEXT_TIMEOUT_MS = 150;
const DEFAULT_MEMORY_DOCUMENT_TAIL_BYTES = 256 * 1024;
const DEFAULT_MEMORY_COMPACT_TURN_INTERVAL = 50;
const DEFAULT_MEMORY_COMPACT_DOCUMENTS_MAX = 1200;
const DEFAULT_MEMORY_COMPACT_DOCUMENTS_KEEP = 600;

type MemoryDocumentCacheEntry = {
  size: number;
  mtimeMs: number;
  maxBytes: number;
  maxDocuments: number;
  documents: MemoryDocument[];
  lastAccessedAtMs: number;
};

const memoryDocumentCache = new Map<string, MemoryDocumentCacheEntry>();
const DEFAULT_MEMORY_DOCUMENT_CACHE_MAX = 64;
const DEFAULT_MEMORY_STATE_CACHE_TTL_MS = 10 * 60 * 1000;
const DEFAULT_MEMORY_STATE_CACHE_MAX = 128;

type CachedMemoryState = {
  expiresAtMs: number;
  lastAccessedAtMs: number;
  state: ChatMemoryState;
};

const memoryStateCache = new Map<string, CachedMemoryState>();

function getMemoryDir(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}) {
  return getDataPath(
    MEMORY_DIR_NAME,
    "chats",
    sanitizePathSegment(input.chatId),
  );
}

function getStatePath(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}) {
  return path.join(getMemoryDir(input), STATE_FILE_NAME);
}

function getRelationshipPath(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}) {
  return path.join(getMemoryDir(input), RELATIONSHIP_FILE_NAME);
}

function getDocumentsPath(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}) {
  return path.join(getMemoryDir(input), DOCUMENTS_FILE_NAME);
}

function getTurnsPath(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}) {
  return path.join(getMemoryDir(input), TURNS_FILE_NAME);
}

export async function readMemoryState(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}): Promise<ChatMemoryState> {
  const statePath = getStatePath(input);
  const cached = readCachedMemoryState(statePath, input);
  if (cached) {
    return cached;
  }

  try {
    const raw = await readJsonFile<unknown | null>(statePath, null);
    const normalizedState = normalizeMemoryState(raw, input);
    const state = {
      ...normalizedState,
      relationship: await readMemoryRelationship(
        input,
        normalizedState.relationship,
      ),
    };
    writeCachedMemoryState(statePath, state);
    return cloneMemoryStateForKey(state, input);
  } catch (error) {
    if (isNotFoundError(error)) {
      const state = createEmptyMemoryState(input);
      writeCachedMemoryState(statePath, state);
      return cloneMemoryStateForKey(state, input);
    }

    throw error;
  }
}

async function readMemoryRelationship(
  input: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
  fallback: MemoryRelationship,
) {
  try {
    const raw = await readJsonFile<unknown | null>(
      getRelationshipPath(input),
      null,
    );
    return raw ? normalizeRelationship(raw) : normalizeRelationship(fallback);
  } catch (error) {
    if (isNotFoundError(error)) {
      return normalizeRelationship(fallback);
    }

    throw error;
  }
}

export async function buildMemoryContext(input: {
  sessionId: string;
  chatId: string;
  character: Character;
  query: string;
}) {
  if (process.env.MEMORY_ENABLED === "0") {
    return "";
  }

  const timeoutMs = getNonNegativeNumberEnv(
    "MEMORY_CONTEXT_TIMEOUT_MS",
    DEFAULT_MEMORY_CONTEXT_TIMEOUT_MS,
  );
  const context = buildMemoryContextCore(input).catch(() => "");

  if (timeoutMs === 0) {
    return context;
  }

  return Promise.race([context, delay(timeoutMs).then(() => "")]);
}

async function buildMemoryContextCore(input: {
  sessionId: string;
  chatId: string;
  character: Character;
  query: string;
}) {
  if (!shouldBuildMemoryContext(input.query)) {
    return "";
  }

  const key = {
    sessionId: input.sessionId,
    chatId: input.chatId,
    characterId: input.character.id,
  };
  const shouldSearchDocuments = shouldSearchMemoryDocuments(input.query);

  const [state, documents] = await Promise.all([
    readMemoryState(key),
    shouldSearchDocuments ? readMemoryDocuments(key) : Promise.resolve([]),
  ]);

  const contextItemChars = getNumberEnv(
    "MEMORY_CONTEXT_ITEM_CHARS",
    DEFAULT_MEMORY_CONTEXT_ITEM_CHARS,
  );
  const relevantDocuments = rankMemoryDocuments(documents, input.query).slice(
    0,
    getNumberEnv("MEMORY_RAG_TOP_K", DEFAULT_MEMORY_RAG_TOP_K),
  );
  const recentEvents = state.events
    .slice()
    .sort((left, right) => right.importance - left.importance)
    .slice(
      0,
      getNumberEnv("MEMORY_RECENT_EVENTS", DEFAULT_MEMORY_RECENT_EVENTS),
    );
  const chunks = state.chunks.slice(
    -getNumberEnv("MEMORY_CONTEXT_CHUNKS", DEFAULT_MEMORY_CONTEXT_CHUNKS),
  );
  const graphEdges = state.graph.slice(
    0,
    getNumberEnv(
      "MEMORY_CONTEXT_GRAPH_EDGES",
      DEFAULT_MEMORY_CONTEXT_GRAPH_EDGES,
    ),
  );
  const summary = truncateForPrompt(
    state.summary,
    getNumberEnv(
      "MEMORY_CONTEXT_SUMMARY_CHARS",
      DEFAULT_MEMORY_CONTEXT_SUMMARY_CHARS,
    ),
  );

  const sections = [
    Object.keys(state.profile).length
      ? `Chat-specific user profile and stable facts:\n${formatProfile(state.profile)}`
      : "",
    Object.keys(state.preferences).length
      ? `Chat-specific reply preferences:\n${formatProfile(state.preferences)}`
      : "",
    formatRelationshipContext(state.relationship),
    summary ? `Current chat summary:\n${summary}` : "",
    recentEvents.length
      ? `Important shared events:\n${recentEvents
          .map(
            (event) =>
              `- ${event.title}: ${truncateForPrompt(
                event.description,
                contextItemChars,
              )}`,
          )
          .join("\n")}`
      : "",
    graphEdges.length
      ? `Relationship graph:\n${graphEdges
          .map(
            (edge) => `- ${edge.subject} --${edge.relation}--> ${edge.object}`,
          )
          .join("\n")}`
      : "",
    chunks.length
      ? `Long conversation chunk summaries:\n${chunks
          .map(
            (chunk) => `- ${truncateForPrompt(chunk.text, contextItemChars)}`,
          )
          .join("\n")}`
      : "",
    relevantDocuments.length
      ? `Relevant remembered details:\n${relevantDocuments
          .map(
            (document) =>
              `- ${truncateForPrompt(document.text, contextItemChars)}`,
          )
          .join("\n")}`
      : "",
  ].filter(Boolean);

  if (!sections.length) {
    return "";
  }

  return [
    "Long-term memory for this single chat follows.",
    "Use these memories naturally and consistently when relevant. Do not list or expose memory metadata unless the user asks about memory. If the latest user message conflicts with memory, follow the latest explicit user message.",
    ...sections,
  ].join("\n\n");
}

function truncateForPrompt(value: string, maxChars: number) {
  const normalized = value.trim().replace(/\s+/g, " ");
  if (!normalized || normalized.length <= maxChars) {
    return normalized;
  }

  return `${normalized.slice(0, Math.max(0, maxChars - 3)).trimEnd()}...`;
}

function shouldBuildMemoryContext(query: string) {
  if (process.env.MEMORY_SELECTIVE_RETRIEVAL === "0") {
    return true;
  }

  const normalized = query.trim();
  if (!normalized) {
    return false;
  }

  if (hasMemoryTrigger(normalized)) {
    return true;
  }

  if (isLowSignalChat(normalized)) {
    return false;
  }

  return compactLength(normalized) >= 24 || tokenizeForSignal(normalized) >= 5;
}

function shouldSearchMemoryDocuments(query: string) {
  if (process.env.MEMORY_SELECTIVE_RETRIEVAL === "0") {
    return true;
  }

  const normalized = query.trim();
  return hasMemoryTrigger(normalized) || compactLength(normalized) >= 40;
}

function hasMemoryTrigger(input: string) {
  return /기억|예전|전에|지난|저번|그때|말했|말한|알려준|약속|계획|설정|관계|이름|좋아|싫어|선호|말투|엄마|아빠|어머니|아버지|동생|형|누나|언니|오빠|친구|가족|회사|학교|프로젝트|내\s*(?:이름|취향|말투|엄마|아빠|동생|형|누나|언니|오빠|친구|가족|회사|학교|프로젝트)|우리\s*(?:엄마|아빠|어머니|아버지|동생|형|누나|언니|오빠|친구|가족|회사|학교|프로젝트)/u.test(
    input,
  );
}

function isLowSignalChat(input: string) {
  const compact = input.replace(/\s+/g, "");
  if (compact.length <= 2) {
    return true;
  }

  return /^(ㅋ+|ㅎ+|ㅠ+|ㅜ+|ㅇ+|응+|어+|네+|넵+|예+|아+|오+|와+|헐+|안녕+|하이+|hi+|hello+|ok+|ㅇㅋ+)[.!?~…]*$/iu.test(
    compact,
  );
}

function compactLength(input: string) {
  return input.replace(/\s+/g, "").length;
}

function tokenizeForSignal(input: string) {
  return input.match(/[a-z0-9\uac00-\ud7a3]{2,}/giu)?.length ?? 0;
}

export async function appendMemoryTurn(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
  turn: MemoryTurn;
}) {
  const dir = getMemoryDir(input);
  const now = new Date().toISOString();
  const record = {
    id: crypto.randomUUID(),
    createdAt: now,
    userContent: input.turn.userContent,
    assistantContent: input.turn.assistantContent,
    messages: input.turn.messages,
  };

  await mkdir(dir, { recursive: true });
  const turnsPath = getTurnsPath(input);
  await withFileLock(turnsPath, async () => {
    await appendFile(turnsPath, `${JSON.stringify(record)}\n`, "utf8");
  });
  await appendMemoryDocuments(input, [
    {
      id: crypto.randomUUID(),
      kind: "turn",
      text: `User: ${input.turn.userContent}\nAssistant: ${input.turn.assistantContent}`,
      importance: 0.55,
      createdAt: now,
    },
  ]);
}

export async function applyMemoryUpdate(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
  turn: MemoryTurn;
  turnCountIncrement?: number;
  update?: MemoryUpdate | null;
}) {
  await withFileLock(getStatePath(input), async () => {
    const state = await readMemoryState(input);
    const now = new Date().toISOString();
    const turnCountIncrement = Math.max(1, input.turnCountIncrement ?? 1);
    const nextState: ChatMemoryState = {
      ...state,
      updatedAt: now,
      turnCount: state.turnCount + turnCountIncrement,
      summary:
        normalizeSummary(input.update?.summary) ||
        updateFallbackSummary(state, input.turn),
      profile: {
        ...state.profile,
        ...normalizeProfile(input.update?.profile),
        ...extractSimpleProfile(input.turn.userContent),
      },
      preferences: {
        ...state.preferences,
        ...normalizeProfile(input.update?.preferences),
        ...extractSimplePreferences(input.turn.userContent),
      },
      relationship: normalizeRelationshipUpdate(
        state.relationship,
        input.update?.relationship,
        now,
      ),
      events: mergeEvents(
        state.events,
        normalizeEvents(input.update?.events, now),
      ),
      graph: mergeGraph(state.graph, normalizeGraph(input.update?.graph)),
      chunks: updateMemoryChunks(state, input.turn, now, turnCountIncrement),
    };

    await Promise.all([
      writeMemoryState(input, nextState),
      writeMemoryRelationship(input, nextState.relationship),
    ]);

    const documents = normalizeDocuments(input.update?.documents, now);
    if (nextState.summary) {
      documents.push({
        id: crypto.randomUUID(),
        kind: "summary",
        text: nextState.summary,
        importance: 0.7,
        createdAt: now,
      });
    }

    for (const event of nextState.events.slice(-3)) {
      documents.push({
        id: crypto.randomUUID(),
        kind: "event",
        text: `${event.title}: ${event.description}`,
        importance: event.importance,
        createdAt: now,
      });
    }

    if (Object.keys(nextState.profile).length) {
      documents.push({
        id: crypto.randomUUID(),
        kind: "profile",
        text: formatProfile(nextState.profile),
        importance: 0.85,
        createdAt: now,
      });
    }

    if (Object.keys(nextState.preferences).length) {
      documents.push({
        id: crypto.randomUUID(),
        kind: "preference",
        text: `Preferences:\n${formatProfile(nextState.preferences)}`,
        importance: 0.82,
        createdAt: now,
      });
    }

    documents.push({
      id: crypto.randomUUID(),
      kind: "relationship",
      text: formatRelationshipContext(nextState.relationship),
      importance: 0.8,
      createdAt: now,
    });

    await appendMemoryDocuments(input, documents);
    await compactMemoryDocumentsIfNeeded(input, nextState, turnCountIncrement);
  });
}

function createEmptyMemoryState(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}): ChatMemoryState {
  return {
    version: 1,
    sessionId: input.sessionId,
    chatId: input.chatId,
    characterId: input.characterId,
    updatedAt: new Date(0).toISOString(),
    turnCount: 0,
    summary: "",
    profile: {},
    preferences: {},
    relationship: createEmptyRelationship(),
    events: [],
    graph: [],
    chunks: [],
  };
}

function normalizeMemoryState(
  input: unknown,
  key: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
): ChatMemoryState {
  if (!input || typeof input !== "object") {
    return createEmptyMemoryState(key);
  }

  const record = input as Partial<ChatMemoryState>;
  return {
    version: 1,
    sessionId: key.sessionId,
    chatId: key.chatId,
    characterId: key.characterId,
    updatedAt:
      typeof record.updatedAt === "string"
        ? record.updatedAt
        : new Date(0).toISOString(),
    turnCount: Number.isFinite(record.turnCount) ? Number(record.turnCount) : 0,
    summary: normalizeSummary(record.summary),
    profile: normalizeProfile(record.profile),
    preferences: normalizeProfile(record.preferences),
    relationship: normalizeRelationship(record.relationship),
    events: normalizeStoredEvents(record.events),
    graph: normalizeGraph(record.graph),
    chunks: normalizeStoredDocuments(record.chunks).slice(-MAX_CHUNKS),
  };
}

async function writeMemoryState(
  input: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
  state: ChatMemoryState,
) {
  const statePath = getStatePath(input);
  await writeJsonFile(statePath, state);
  writeCachedMemoryState(statePath, state);
}

async function writeMemoryRelationship(
  input: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
  relationship: MemoryRelationship,
) {
  await writeJsonFile(getRelationshipPath(input), normalizeRelationship(relationship));
}

function readCachedMemoryState(
  statePath: string,
  key: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
) {
  const cached = memoryStateCache.get(statePath);
  const now = Date.now();
  if (!cached || cached.expiresAtMs <= now) {
    if (cached) {
      memoryStateCache.delete(statePath);
    }
    return null;
  }

  cached.lastAccessedAtMs = now;
  return cloneMemoryStateForKey(cached.state, key);
}

function writeCachedMemoryState(statePath: string, state: ChatMemoryState) {
  const ttlMs = getNonNegativeNumberEnv(
    "MEMORY_STATE_CACHE_TTL_MS",
    DEFAULT_MEMORY_STATE_CACHE_TTL_MS,
  );
  if (ttlMs === 0) {
    memoryStateCache.delete(statePath);
    return;
  }

  const now = Date.now();
  memoryStateCache.set(statePath, {
    expiresAtMs: now + ttlMs,
    lastAccessedAtMs: now,
    state: cloneMemoryStateForKey(state, state),
  });
  pruneMemoryStateCache(now);
}

function pruneMemoryStateCache(now = Date.now()) {
  for (const [statePath, cached] of memoryStateCache) {
    if (cached.expiresAtMs <= now) {
      memoryStateCache.delete(statePath);
    }
  }

  const maxEntries = getNumberEnv(
    "MEMORY_STATE_CACHE_MAX",
    DEFAULT_MEMORY_STATE_CACHE_MAX,
  );
  while (memoryStateCache.size > maxEntries) {
    let oldestPath = "";
    let oldestAccessedAtMs = Number.POSITIVE_INFINITY;
    for (const [statePath, cached] of memoryStateCache) {
      if (cached.lastAccessedAtMs < oldestAccessedAtMs) {
        oldestPath = statePath;
        oldestAccessedAtMs = cached.lastAccessedAtMs;
      }
    }
    if (!oldestPath) {
      break;
    }
    memoryStateCache.delete(oldestPath);
  }
}

function cloneMemoryStateForKey(
  state: ChatMemoryState,
  key: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
): ChatMemoryState {
  return {
    ...state,
    sessionId: key.sessionId,
    chatId: key.chatId,
    characterId: key.characterId,
    profile: { ...state.profile },
    preferences: { ...state.preferences },
    relationship: {
      ...state.relationship,
      openLoops: [...state.relationship.openLoops],
      boundaries: [...state.relationship.boundaries],
    },
    events: state.events.map((event) => ({ ...event })),
    graph: state.graph.map((edge) => ({ ...edge })),
    chunks: state.chunks.map((chunk) => ({ ...chunk })),
  };
}

function pruneMemoryDocumentCache() {
  const maxEntries = getNumberEnv(
    "MEMORY_DOCUMENT_CACHE_MAX",
    DEFAULT_MEMORY_DOCUMENT_CACHE_MAX,
  );

  while (memoryDocumentCache.size > maxEntries) {
    let oldestPath = "";
    let oldestAccessedAtMs = Number.POSITIVE_INFINITY;
    for (const [filePath, cached] of memoryDocumentCache) {
      if (cached.lastAccessedAtMs < oldestAccessedAtMs) {
        oldestPath = filePath;
        oldestAccessedAtMs = cached.lastAccessedAtMs;
      }
    }

    if (!oldestPath) {
      break;
    }

    memoryDocumentCache.delete(oldestPath);
  }
}

async function readMemoryDocuments(input: {
  sessionId: string;
  chatId: string;
  characterId: string;
}) {
  const filePath = getDocumentsPath(input);
  const maxBytes = getNumberEnv(
    "MEMORY_DOCUMENT_TAIL_BYTES",
    DEFAULT_MEMORY_DOCUMENT_TAIL_BYTES,
  );
  const maxDocuments = getNumberEnv("MEMORY_SEARCH_MAX_DOCUMENTS", 400);

  try {
    const stats = await stat(filePath);
    const cached = memoryDocumentCache.get(filePath);
    if (
      cached &&
      cached.size === stats.size &&
      cached.mtimeMs === stats.mtimeMs &&
      cached.maxBytes === maxBytes &&
      cached.maxDocuments === maxDocuments
    ) {
      cached.lastAccessedAtMs = Date.now();
      return cached.documents;
    }

    const raw = await readRecentFileText(filePath, maxBytes);
    const documents = raw
      .split("\n")
      .filter(Boolean)
      .slice(-maxDocuments)
      .map(parseMemoryDocumentLine)
      .filter((document) => document.text);
    memoryDocumentCache.set(filePath, {
      size: stats.size,
      mtimeMs: stats.mtimeMs,
      maxBytes,
      maxDocuments,
      documents,
      lastAccessedAtMs: Date.now(),
    });
    pruneMemoryDocumentCache();

    return documents;
  } catch (error) {
    if (isNotFoundError(error)) {
      memoryDocumentCache.delete(filePath);
      return [];
    }

    throw error;
  }
}

async function readRecentFileText(filePath: string, maxBytes: number) {
  const file = await open(filePath, "r");

  try {
    const stats = await file.stat();
    const bytesToRead = Math.min(stats.size, maxBytes);
    const start = Math.max(0, stats.size - bytesToRead);
    const buffer = Buffer.alloc(bytesToRead);
    await file.read(buffer, 0, bytesToRead, start);
    let text = buffer.toString("utf8");

    if (start > 0) {
      const firstFullLineIndex = text.indexOf("\n");
      text = firstFullLineIndex >= 0 ? text.slice(firstFullLineIndex + 1) : "";
    }

    return text;
  } finally {
    await file.close();
  }
}

async function appendMemoryDocuments(
  input: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
  documents: MemoryDocument[],
) {
  if (!documents.length) {
    return;
  }

  const filePath = getDocumentsPath(input);
  await withFileLock(filePath, async () => {
    await mkdir(path.dirname(filePath), { recursive: true });
    await appendFile(
      filePath,
      documents.map((document) => JSON.stringify(document)).join("\n") + "\n",
      "utf8",
    );
    await updateMemoryDocumentCacheAfterAppend(filePath, documents);
  });
}

async function updateMemoryDocumentCacheAfterAppend(
  filePath: string,
  documents: MemoryDocument[],
) {
  const cached = memoryDocumentCache.get(filePath);
  if (!cached) {
    return;
  }

  try {
    const stats = await stat(filePath);
    memoryDocumentCache.set(filePath, {
      ...cached,
      size: stats.size,
      mtimeMs: stats.mtimeMs,
      documents: [...cached.documents, ...documents].slice(-cached.maxDocuments),
      lastAccessedAtMs: Date.now(),
    });
    pruneMemoryDocumentCache();
  } catch {
    memoryDocumentCache.delete(filePath);
  }
}

async function compactMemoryDocumentsIfNeeded(
  input: {
    sessionId: string;
    chatId: string;
    characterId: string;
  },
  state: ChatMemoryState,
  turnCountIncrement: number,
) {
  const interval = getNonNegativeNumberEnv(
    "MEMORY_COMPACT_TURN_INTERVAL",
    DEFAULT_MEMORY_COMPACT_TURN_INTERVAL,
  );
  const previousTurnCount = Math.max(0, state.turnCount - turnCountIncrement);
  if (
    interval === 0 ||
    Math.floor(previousTurnCount / interval) ===
      Math.floor(state.turnCount / interval)
  ) {
    return;
  }

  const maxDocuments = getNumberEnv(
    "MEMORY_COMPACT_DOCUMENTS_MAX",
    DEFAULT_MEMORY_COMPACT_DOCUMENTS_MAX,
  );
  const keepDocuments = Math.min(
    maxDocuments,
    getNumberEnv(
      "MEMORY_COMPACT_DOCUMENTS_KEEP",
      DEFAULT_MEMORY_COMPACT_DOCUMENTS_KEEP,
    ),
  );
  const filePath = getDocumentsPath(input);

  try {
    await withFileLock(filePath, async () => {
      const raw = await readRecentFileText(
        filePath,
        getNumberEnv("MEMORY_COMPACT_READ_BYTES", 4 * 1024 * 1024),
      );
      const documents = raw
        .split("\n")
        .filter(Boolean)
        .map(parseMemoryDocumentLine)
        .filter((document) => document.text);

      if (documents.length <= maxDocuments) {
        return;
      }

      const compactedDocuments = dedupeMemoryDocuments([
        ...documents.slice(-keepDocuments),
        ...createStateSnapshotDocuments(state, new Date().toISOString()),
      ]).slice(-maxDocuments);

      await writeTextFile(
        filePath,
        compactedDocuments.map((document) => JSON.stringify(document)).join("\n") +
          "\n",
      );
      await refreshMemoryDocumentCacheAfterRewrite(filePath, compactedDocuments);
    });
  } catch (error) {
    if (isNotFoundError(error)) {
      memoryDocumentCache.delete(filePath);
      return;
    }

    throw error;
  }
}

function createStateSnapshotDocuments(state: ChatMemoryState, now: string) {
  const documents: MemoryDocument[] = [];
  if (state.summary) {
    documents.push({
      id: crypto.randomUUID(),
      kind: "summary",
      text: state.summary,
      importance: 0.72,
      createdAt: now,
    });
  }
  if (Object.keys(state.profile).length) {
    documents.push({
      id: crypto.randomUUID(),
      kind: "profile",
      text: formatProfile(state.profile),
      importance: 0.86,
      createdAt: now,
    });
  }
  if (Object.keys(state.preferences).length) {
    documents.push({
      id: crypto.randomUUID(),
      kind: "preference",
      text: `Preferences:\n${formatProfile(state.preferences)}`,
      importance: 0.83,
      createdAt: now,
    });
  }
  documents.push({
    id: crypto.randomUUID(),
    kind: "relationship",
    text: formatRelationshipContext(state.relationship),
    importance: 0.82,
    createdAt: now,
  });
  for (const event of state.events.slice(-8)) {
    documents.push({
      id: crypto.randomUUID(),
      kind: "event",
      text: `${event.title}: ${event.description}`,
      importance: event.importance,
      createdAt: event.createdAt,
    });
  }
  documents.push(...state.chunks.slice(-8));

  return documents;
}

function dedupeMemoryDocuments(documents: MemoryDocument[]) {
  const seen = new Set<string>();
  const deduped: MemoryDocument[] = [];
  for (const document of documents.slice().reverse()) {
    const key = `${document.kind}|${document.text.toLowerCase()}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(document);
  }

  return deduped.reverse();
}

async function refreshMemoryDocumentCacheAfterRewrite(
  filePath: string,
  documents: MemoryDocument[],
) {
  try {
    const stats = await stat(filePath);
    const maxBytes = getNumberEnv(
      "MEMORY_DOCUMENT_TAIL_BYTES",
      DEFAULT_MEMORY_DOCUMENT_TAIL_BYTES,
    );
    const maxDocuments = getNumberEnv("MEMORY_SEARCH_MAX_DOCUMENTS", 400);
    if (stats.size > maxBytes) {
      memoryDocumentCache.delete(filePath);
      return;
    }

    memoryDocumentCache.set(filePath, {
      size: stats.size,
      mtimeMs: stats.mtimeMs,
      maxBytes,
      maxDocuments,
      documents: documents.slice(-maxDocuments),
      lastAccessedAtMs: Date.now(),
    });
    pruneMemoryDocumentCache();
  } catch {
    memoryDocumentCache.delete(filePath);
  }
}

function parseMemoryDocumentLine(line: string): MemoryDocument {
  try {
    const document = JSON.parse(line) as Partial<MemoryDocument>;
    return {
      id: typeof document.id === "string" ? document.id : crypto.randomUUID(),
      kind: isMemoryDocumentKind(document.kind) ? document.kind : "turn",
      text: typeof document.text === "string" ? document.text : "",
      importance:
        typeof document.importance === "number" &&
        Number.isFinite(document.importance)
          ? document.importance
          : 0.5,
      createdAt:
        typeof document.createdAt === "string"
          ? document.createdAt
          : new Date(0).toISOString(),
    };
  } catch {
    return {
      id: crypto.randomUUID(),
      kind: "turn",
      text: "",
      importance: 0,
      createdAt: new Date(0).toISOString(),
    };
  }
}

function isMemoryDocumentKind(value: unknown): value is MemoryDocumentKind {
  return (
    value === "turn" ||
    value === "event" ||
    value === "summary" ||
    value === "profile" ||
    value === "preference" ||
    value === "relationship"
  );
}

function normalizeSummary(value: unknown) {
  return typeof value === "string"
    ? value.trim().slice(0, MAX_SUMMARY_CHARS)
    : "";
}

function normalizeProfile(input: unknown): MemoryProfile {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return {};
  }

  const profile: MemoryProfile = {};
  for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
    if (typeof value === "string" && value.trim()) {
      const cleanKey = sanitizeProfileKey(key);
      if (cleanKey) {
        profile[cleanKey] = value.trim().slice(0, 240);
      }
    }
  }

  return profile;
}

function sanitizeProfileKey(key: string) {
  return key
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\uac00-\ud7a3_-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
}

function normalizeEvents(input: unknown, now: string): MemoryEvent[] {
  if (!Array.isArray(input)) {
    return [];
  }

  const events: MemoryEvent[] = [];
  for (const event of input) {
    if (!event || typeof event !== "object") {
      continue;
    }

    const record = event as Record<string, unknown>;
    const title = typeof record.title === "string" ? record.title.trim() : "";
    const description =
      typeof record.description === "string" ? record.description.trim() : "";

    if (!title || !description) {
      continue;
    }

    events.push({
      id: crypto.randomUUID(),
      title: title.slice(0, 120),
      description: description.slice(0, 600),
      emotion:
        typeof record.emotion === "string"
          ? record.emotion.trim().slice(0, 80)
          : undefined,
      importance: clampImportance(record.importance),
      createdAt: now,
    });
  }

  return events;
}

function normalizeStoredEvents(input: unknown): MemoryEvent[] {
  if (!Array.isArray(input)) {
    return [];
  }

  const events: MemoryEvent[] = [];
  for (const event of input) {
    if (!event || typeof event !== "object") {
      continue;
    }

    const record = event as MemoryEvent;
    if (!record.title || !record.description) {
      continue;
    }

    events.push({
      id: typeof record.id === "string" ? record.id : crypto.randomUUID(),
      title: String(record.title).slice(0, 120),
      description: String(record.description).slice(0, 600),
      emotion:
        typeof record.emotion === "string"
          ? record.emotion.slice(0, 80)
          : undefined,
      importance: clampImportance(record.importance),
      createdAt:
        typeof record.createdAt === "string"
          ? record.createdAt
          : new Date().toISOString(),
    });
  }

  return events.slice(-MAX_EVENTS);
}

function normalizeGraph(input: unknown): MemoryEdge[] {
  if (!Array.isArray(input)) {
    return [];
  }

  return input
    .map((edge) => {
      if (!edge || typeof edge !== "object") {
        return null;
      }

      const record = edge as Record<string, unknown>;
      const subject =
        typeof record.subject === "string" ? record.subject.trim() : "";
      const relation =
        typeof record.relation === "string" ? record.relation.trim() : "";
      const object =
        typeof record.object === "string" ? record.object.trim() : "";

      if (!subject || !relation || !object) {
        return null;
      }

      return {
        subject: subject.slice(0, 80),
        relation: relation.slice(0, 80),
        object: object.slice(0, 120),
      };
    })
    .filter((edge): edge is MemoryEdge => edge !== null);
}

function normalizeDocuments(input: unknown, now: string): MemoryDocument[] {
  if (!Array.isArray(input)) {
    return [];
  }

  return input
    .map((document) => {
      if (!document || typeof document !== "object") {
        return null;
      }

      const record = document as Record<string, unknown>;
      const text = typeof record.text === "string" ? record.text.trim() : "";
      const kind = normalizeDocumentKind(record.kind);

      if (!text) {
        return null;
      }

      return {
        id: crypto.randomUUID(),
        kind,
        text: text.slice(0, 1000),
        importance: clampImportance(record.importance),
        createdAt: now,
      };
    })
    .filter((document): document is MemoryDocument => document !== null);
}

function normalizeStoredDocuments(input: unknown): MemoryDocument[] {
  if (!Array.isArray(input)) {
    return [];
  }

  return input
    .map((document) => {
      if (!document || typeof document !== "object") {
        return null;
      }

      const record = document as Partial<MemoryDocument>;
      const text = typeof record.text === "string" ? record.text.trim() : "";
      if (!text) {
        return null;
      }

      return {
        id: typeof record.id === "string" ? record.id : crypto.randomUUID(),
        kind: normalizeDocumentKind(record.kind),
        text: text.slice(0, 1000),
        importance: clampImportance(record.importance),
        createdAt:
          typeof record.createdAt === "string"
            ? record.createdAt
            : new Date().toISOString(),
      };
    })
    .filter((document): document is MemoryDocument => document !== null);
}

function normalizeDocumentKind(value: unknown): MemoryDocumentKind {
  return value === "event" ||
    value === "summary" ||
    value === "profile" ||
    value === "preference" ||
    value === "relationship"
    ? value
    : "turn";
}

function clampImportance(value: unknown) {
  const numberValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numberValue)) {
    return 0.5;
  }

  return Math.min(1, Math.max(0, numberValue));
}

function mergeEvents(existing: MemoryEvent[], incoming: MemoryEvent[]) {
  const seen = new Set<string>();
  const merged = [...existing, ...incoming].filter((event) => {
    const key = `${event.title.toLowerCase()}|${event.description.toLowerCase()}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });

  return merged.slice(-MAX_EVENTS);
}

function mergeGraph(existing: MemoryEdge[], incoming: MemoryEdge[]) {
  const seen = new Set<string>();
  return [...existing, ...incoming]
    .filter((edge) => {
      const key =
        `${edge.subject}|${edge.relation}|${edge.object}`.toLowerCase();
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    })
    .slice(-MAX_GRAPH_EDGES);
}

function formatProfile(profile: MemoryProfile) {
  return Object.entries(profile)
    .map(([key, value]) => `- ${key}: ${value}`)
    .join("\n");
}

function createEmptyRelationship(): MemoryRelationship {
  return {
    intimacy: 0.2,
    trust: 0.2,
    mood: "new",
    dynamic: "getting to know each other",
    openLoops: [],
    boundaries: [],
  };
}

function normalizeRelationship(input: unknown): MemoryRelationship {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return createEmptyRelationship();
  }

  const record = input as Partial<MemoryRelationship>;
  return {
    intimacy: clampImportance(record.intimacy),
    trust: clampImportance(record.trust),
    mood:
      typeof record.mood === "string" && record.mood.trim()
        ? record.mood.trim().slice(0, 120)
        : "new",
    dynamic:
      typeof record.dynamic === "string" && record.dynamic.trim()
        ? record.dynamic.trim().slice(0, 240)
        : "getting to know each other",
    openLoops: normalizeShortStringList(record.openLoops, 12, 160),
    boundaries: normalizeShortStringList(record.boundaries, 12, 160),
    lastInteractionAt:
      typeof record.lastInteractionAt === "string"
        ? record.lastInteractionAt
        : undefined,
  };
}

function normalizeRelationshipUpdate(
  current: MemoryRelationship,
  update: unknown,
  now: string,
): MemoryRelationship {
  const normalizedCurrent = normalizeRelationship(current);
  if (!update || typeof update !== "object" || Array.isArray(update)) {
    return {
      ...normalizedCurrent,
      lastInteractionAt: now,
    };
  }

  const incoming = update as Partial<MemoryRelationship>;
  return {
    intimacy:
      incoming.intimacy === undefined
        ? normalizedCurrent.intimacy
        : clampImportance(incoming.intimacy),
    trust:
      incoming.trust === undefined
        ? normalizedCurrent.trust
        : clampImportance(incoming.trust),
    mood:
      typeof incoming.mood === "string" && incoming.mood.trim()
        ? incoming.mood.trim().slice(0, 120)
        : normalizedCurrent.mood,
    dynamic:
      typeof incoming.dynamic === "string" && incoming.dynamic.trim()
        ? incoming.dynamic.trim().slice(0, 240)
        : normalizedCurrent.dynamic,
    openLoops: mergeStringList(
      normalizedCurrent.openLoops,
      normalizeShortStringList(incoming.openLoops, 12, 160),
      12,
    ),
    boundaries: mergeStringList(
      normalizedCurrent.boundaries,
      normalizeShortStringList(incoming.boundaries, 12, 160),
      12,
    ),
    lastInteractionAt: now,
  };
}

function normalizeShortStringList(
  input: unknown,
  maxItems: number,
  maxChars: number,
) {
  if (!Array.isArray(input)) {
    return [];
  }

  return input
    .filter((item): item is string => typeof item === "string" && !!item.trim())
    .map((item) => item.trim().replace(/\s+/g, " ").slice(0, maxChars))
    .slice(0, maxItems);
}

function mergeStringList(
  existing: string[],
  incoming: string[],
  maxItems: number,
) {
  const seen = new Set<string>();
  return [...existing, ...incoming]
    .filter((item) => {
      const key = item.toLowerCase();
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    })
    .slice(-maxItems);
}

function formatRelationshipContext(relationship: MemoryRelationship) {
  const normalized = normalizeRelationship(relationship);
  const lines = [
    `- intimacy: ${normalized.intimacy.toFixed(2)}`,
    `- trust: ${normalized.trust.toFixed(2)}`,
    `- mood: ${normalized.mood}`,
    `- dynamic: ${normalized.dynamic}`,
    normalized.openLoops.length
      ? `- open loops: ${normalized.openLoops.join("; ")}`
      : "",
    normalized.boundaries.length
      ? `- boundaries: ${normalized.boundaries.join("; ")}`
      : "",
  ].filter(Boolean);

  return `Relationship state:\n${lines.join("\n")}`;
}

function updateMemoryChunks(
  state: ChatMemoryState,
  turn: MemoryTurn,
  now: string,
  turnCountIncrement = 1,
): MemoryDocument[] {
  const interval = getNumberEnv("MEMORY_CHUNK_TURN_INTERVAL", 25);
  const nextTurnCount = state.turnCount + turnCountIncrement;
  if (nextTurnCount % interval !== 0) {
    return state.chunks;
  }

  const chunkText = [
    state.summary,
    `Latest: User: ${turn.userContent} / Assistant: ${turn.assistantContent}`,
  ]
    .filter(Boolean)
    .join("\n")
    .replace(/\s+/g, " ")
    .slice(0, 1000);
  const chunk: MemoryDocument = {
    id: crypto.randomUUID(),
    kind: "summary",
    text: chunkText,
    importance: 0.78,
    createdAt: now,
  };

  return [...state.chunks, chunk].slice(-MAX_CHUNKS);
}

function updateFallbackSummary(state: ChatMemoryState, turn: MemoryTurn) {
  const latest = `User: ${turn.userContent}\nAssistant: ${turn.assistantContent}`;
  return [state.summary, latest]
    .filter(Boolean)
    .join("\n")
    .slice(-MAX_SUMMARY_CHARS);
}

function extractSimpleProfile(input: string): MemoryProfile {
  const profile: MemoryProfile = {};
  const patterns: Array<[RegExp, string]> = [
    [
      /\ub0b4\s*\uc774\ub984\uc740\s*([^\s,.!?]{1,30})(?:\uc774\uc57c|\uc57c|\uc785\ub2c8\ub2e4)?/u,
      "user_name",
    ],
    [/\ub098\ub294\s*([^,.!?]{1,30})\s*\uc88b\uc544/u, "user_likes"],
    [/\ub098\ub294\s*([^,.!?]{1,30})\s*\uc2eb\uc5b4/u, "user_dislikes"],
    [
      /(?:\ub0b4\s*)?(?:\uace0\uc591\uc774|\uac15\uc544\uc9c0|\ubc18\ub824\ub3d9\ubb3c)\s*\uc774\ub984\uc740\s*([^\s,.!?]{1,30})/u,
      "pet_name",
    ],
    [
      /\ub098\ub294\s*([^,.!?]{1,30})\s*(?:\uc368|\uc0ac\uc6a9\ud574)/u,
      "user_device",
    ],
  ];

  for (const [pattern, key] of patterns) {
    const match = input.match(pattern);
    if (match) {
      profile[key] = match.slice(1).filter(Boolean).join(" ").trim();
    }
  }

  return profile;
}

function extractSimplePreferences(input: string): MemoryProfile {
  const preferences: MemoryProfile = {};
  const patterns: Array<[RegExp, string]> = [
    [
      /(?:\ub2f5\ubcc0|\ub9d0)\s*(?:\uc9e7\uac8c|\uac04\ub2e8\ud788)\s*\ud574/u,
      "answer_length",
    ],
    [
      /(?:\ub2f5\ubcc0|\ub9d0)\s*(?:\uc790\uc138\ud788|\uae38\uac8c)\s*\ud574/u,
      "answer_detail",
    ],
    [/\ud55c\uad6d\uc5b4\ub85c\s*(?:\ub9d0\ud574|\ub2f5\ud574)/u, "language"],
    [
      /(?:\ubc18\ub9d0|\uce5c\uadfc\ud558\uac8c)\s*(?:\ud574|\ub9d0\ud574)/u,
      "tone",
    ],
    [
      /(?:\uc874\ub313\ub9d0|\uacf5\uc190\ud558\uac8c)\s*(?:\ud574|\ub9d0\ud574)/u,
      "tone",
    ],
  ];

  for (const [pattern, key] of patterns) {
    const match = input.match(pattern);
    if (match) {
      preferences[key] = match[0].trim().slice(0, 120);
    }
  }

  return preferences;
}

function getNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function getNonNegativeNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
