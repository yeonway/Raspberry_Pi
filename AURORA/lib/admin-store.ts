import { appendFile, mkdir, readFile } from "fs/promises";
import path from "path";
import {
  getDataPath,
  isNotFoundError,
  readJsonFile,
  withFileLock,
  writeJsonFile,
} from "@/lib/server-files";

const ADMIN_DIR = "admin";

function adminPath(...segments: string[]) {
  return getDataPath(ADMIN_DIR, ...segments);
}

// ── Types ────────────────────────────────────────────────────────────────────

export type FeatureFlag = {
  key: string;
  label: string;
  description: string;
  status: "off" | "admin" | "all";
  updatedAt: string;
};

export type FeatureFlags = Record<string, FeatureFlag>;

export type AuditLogEntry = {
  id: string;
  category: "character" | "world" | "prompt" | "ai" | "memory" | "operation";
  action: string;
  target: string;
  before?: string;
  after?: string;
  adminUser: string;
  createdAt: string;
};

export type AdminNote = {
  id: string;
  title: string;
  content: string;
  links: string[];
  isArchived: boolean;
  createdAt: string;
  updatedAt: string;
};

export type TrashItem = {
  id: string;
  type: string;
  name: string;
  data: unknown;
  deletedAt: string;
};

export type BackupEntry = {
  id: string;
  filename: string;
  version: string;
  size: number;
  itemCounts: Record<string, number>;
  createdAt: string;
};

export type ErrorReport = {
  id: string;
  type: string;
  message: string;
  stack?: string;
  userId?: string;
  characterId?: string;
  chatId?: string;
  requestInfo?: string;
  status: "new" | "checking" | "resolved" | "ignored";
  createdAt: string;
};

export type AdminNotification = {
  id: string;
  type: "error" | "backup" | "ai" | "parse" | "rate";
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
};

export type ABTestResult = {
  id: string;
  prompt: string;
  model: string;
  configA: { prompt?: string; model?: string; temperature?: number };
  configB: { prompt?: string; model?: string; temperature?: number };
  responseA: string;
  responseB: string;
  winner: "A" | "B" | "tie";
  createdAt: string;
};

export type PromptVersion = {
  id: string;
  promptKey: string;
  content: string;
  createdAt: string;
};

export type ConsistencyTest = {
  id: string;
  question: string;
  createdAt: string;
};

export type DialogueExample = {
  id: string;
  situation: string;
  userInput: string;
  characterResponse: string;
  sortOrder: number;
};

export type SpeechStyle = {
  formality: "polite" | "casual" | "mixed";
  sentenceLength: "short" | "medium" | "long";
  descriptionLevel: "minimal" | "moderate" | "rich";
  questionFrequency: "low" | "medium" | "high";
  catchphrases: string[];
  forbiddenExpressions: string[];
};

export type CharacterExtended = {
  characterId: string;
  knowledge: { known: string[]; unknown: string[] };
  secrets: string[];
  learnable: string[];
  dialogueExamples: DialogueExample[];
  speechStyle: SpeechStyle;
  consistencyTests: ConsistencyTest[];
  updatedAt: string;
};

export type CharacterRelationship = {
  id: string;
  fromCharacterId: string;
  toCharacterId: string;
  relation: string;
  description: string;
  events: string;
  secrets: string;
  createdAt: string;
};

export type Collection = {
  id: string;
  title: string;
  description: string;
  characterIds: string[];
  sortOrder: number;
  isPublic: boolean;
  createdAt: string;
};

export type WorldData = {
  id: string;
  name: string;
  overview: string;
  locations: string;
  organizations: string;
  characters: string;
  history: string;
  events: string;
  rules: string;
  terms: string;
  createdAt: string;
  updatedAt: string;
};

export type Place = {
  id: string;
  name: string;
  description: string;
  atmosphere: string;
  relatedCharacterIds: string[];
  relatedSceneIds: string[];
  relatedLorebookIds: string[];
  createdAt: string;
};

export type LorebookEntry = {
  id: string;
  name: string;
  keywords: string[];
  content: string;
  characterIds: string[];
  worldId?: string;
  priority: number;
  isActive: boolean;
  createdAt: string;
};

export type Asset = {
  id: string;
  name: string;
  type: "character" | "cover" | "scene" | "background" | "other";
  url: string;
  usedBy: string[];
  createdAt: string;
};

export type CollisionResult = {
  type: string;
  source: string;
  target: string;
  description: string;
};

// ── File Helpers ─────────────────────────────────────────────────────────────

const FEATURES_FILE = "features.json";
const AUDIT_FILE = "audit-log.jsonl";
const NOTES_FILE = "notes.json";
const TRASH_FILE = "trash.json";
const BACKUPS_FILE = "backups.json";
const ERRORS_FILE = "errors.json";
const NOTIFICATIONS_FILE = "notifications.json";
const AB_TESTS_FILE = "ab-tests.jsonl";
const CHARACTER_EXTENDED_FILE = "character-extended.json";
const RELATIONSHIPS_FILE = "relationships.json";
const COLLECTIONS_FILE = "collections.json";
const WORLDS_FILE = "worlds.json";
const PLACES_FILE = "places.json";
const LOREBOOKS_FILE = "lorebooks.json";
const ASSETS_FILE = "assets.json";

async function readJsonl<T>(file: string, limit = 500): Promise<T[]> {
  try {
    const raw = await readFile(adminPath(file), "utf8");
    return raw.split("\n").filter(Boolean).map((l) => JSON.parse(l) as T).slice(-limit).reverse();
  } catch (e) { if (isNotFoundError(e)) return []; throw e; }
}

async function appendJsonl(file: string, data: unknown) {
  const filePath = adminPath(file);
  await mkdir(path.dirname(filePath), { recursive: true });
  await withFileLock(filePath, () => appendFile(filePath, `${JSON.stringify(data)}\n`, "utf8"));
}

async function readJson<T>(file: string, fallback: T): Promise<T> {
  return readJsonFile<T>(adminPath(file), fallback, { recoverTrailingData: true });
}

async function writeJson(file: string, data: unknown) {
  const filePath = adminPath(file);
  await withFileLock(filePath, () => writeJsonFile(filePath, data));
}

// ── CRUD Operations ──────────────────────────────────────────────────────────

export async function readFeatureFlags(): Promise<FeatureFlags> {
  return readJson<FeatureFlags>(FEATURES_FILE, {});
}
export async function saveFeatureFlags(flags: FeatureFlags) {
  await writeJson(FEATURES_FILE, flags); return flags;
}

export async function appendAuditLog(e: Omit<AuditLogEntry, "id" | "createdAt">) {
  const item: AuditLogEntry = { ...e, id: crypto.randomUUID(), createdAt: new Date().toISOString() };
  await appendJsonl(AUDIT_FILE, item);
  return item;
}
export async function readAuditLog(limit = 500): Promise<AuditLogEntry[]> {
  return readJsonl<AuditLogEntry>(AUDIT_FILE, limit);
}

export async function readNotes(): Promise<AdminNote[]> {
  return readJson<AdminNote[]>(NOTES_FILE, []);
}
export async function saveNotes(notes: AdminNote[]) {
  await writeJson(NOTES_FILE, notes); return notes;
}

export async function readTrash(): Promise<TrashItem[]> {
  return readJson<TrashItem[]>(TRASH_FILE, []);
}
export async function addToTrash(item: Omit<TrashItem, "id" | "deletedAt">) {
  const trash = await readTrash();
  const entry: TrashItem = { ...item, id: crypto.randomUUID(), deletedAt: new Date().toISOString() };
  trash.unshift(entry);
  await writeJson(TRASH_FILE, trash);
  return entry;
}
export async function restoreFromTrash(id: string): Promise<TrashItem | null> {
  const trash = await readTrash();
  const idx = trash.findIndex((t) => t.id === id);
  if (idx === -1) return null;
  const [item] = trash.splice(idx, 1);
  await writeJson(TRASH_FILE, trash);
  return item;
}
export async function permanentlyDeleteFromTrash(id: string) {
  const trash = await readTrash();
  const next = trash.filter((t) => t.id !== id);
  await writeJson(TRASH_FILE, next);
  return next;
}
export async function emptyTrash() {
  await writeJson(TRASH_FILE, []);
}

export async function readBackups(): Promise<BackupEntry[]> {
  return readJson<BackupEntry[]>(BACKUPS_FILE, []);
}
export async function saveBackups(backups: BackupEntry[]) {
  await writeJson(BACKUPS_FILE, backups); return backups;
}

export async function readErrors(): Promise<ErrorReport[]> {
  return readJson<ErrorReport[]>(ERRORS_FILE, []);
}
export async function saveErrors(errors: ErrorReport[]) {
  await writeJson(ERRORS_FILE, errors); return errors;
}

export async function readNotifications(): Promise<AdminNotification[]> {
  return readJson<AdminNotification[]>(NOTIFICATIONS_FILE, []);
}
export async function saveNotifications(notifs: AdminNotification[]) {
  await writeJson(NOTIFICATIONS_FILE, notifs); return notifs;
}

export async function appendABTestResult(r: Omit<ABTestResult, "id" | "createdAt">) {
  const item: ABTestResult = { ...r, id: crypto.randomUUID(), createdAt: new Date().toISOString() };
  await appendJsonl(AB_TESTS_FILE, item);
  return item;
}
export async function readABTestResults(limit = 200): Promise<ABTestResult[]> {
  return readJsonl<ABTestResult>(AB_TESTS_FILE, limit);
}

export async function savePromptVersion(promptKey: string, content: string) {
  const v: PromptVersion = { id: crypto.randomUUID(), promptKey, content, createdAt: new Date().toISOString() };
  const fn = `prompt-versions/${promptKey.replace(/[^a-z0-9_.-]/g, "_")}.jsonl`;
  await appendJsonl(fn, v);
  return v;
}
export async function readPromptVersions(promptKey: string): Promise<PromptVersion[]> {
  return readJsonl<PromptVersion>(`prompt-versions/${promptKey.replace(/[^a-z0-9_.-]/g, "_")}.jsonl`, 200);
}

export async function readAllCharacterExtended(): Promise<Record<string, CharacterExtended>> {
  return readJson<Record<string, CharacterExtended>>(CHARACTER_EXTENDED_FILE, {});
}
export async function readCharacterExtended(characterId: string): Promise<CharacterExtended | null> {
  const all = await readAllCharacterExtended();
  return all[characterId] ?? null;
}
function defaultCharacterExtended(characterId: string): CharacterExtended {
  return {
    characterId, knowledge: { known: [], unknown: [] }, secrets: [], learnable: [],
    dialogueExamples: [], speechStyle: { formality: "mixed", sentenceLength: "medium",
      descriptionLevel: "moderate", questionFrequency: "medium", catchphrases: [], forbiddenExpressions: [] },
    consistencyTests: [], updatedAt: new Date().toISOString(),
  };
}
export async function saveCharacterExtended(characterId: string, data: Partial<CharacterExtended>) {
  const all = await readAllCharacterExtended();
  all[characterId] = { ...(all[characterId] ?? defaultCharacterExtended(characterId)), ...data, characterId, updatedAt: new Date().toISOString() };
  await writeJson(CHARACTER_EXTENDED_FILE, all);
  return all[characterId];
}

export async function readRelationships(): Promise<CharacterRelationship[]> {
  return readJson<CharacterRelationship[]>(RELATIONSHIPS_FILE, []);
}
export async function saveRelationships(r: CharacterRelationship[]) {
  await writeJson(RELATIONSHIPS_FILE, r); return r;
}

export async function readCollections(): Promise<Collection[]> {
  return readJson<Collection[]>(COLLECTIONS_FILE, []);
}
export async function saveCollections(c: Collection[]) {
  await writeJson(COLLECTIONS_FILE, c); return c;
}

export async function readWorlds(): Promise<WorldData[]> {
  return readJson<WorldData[]>(WORLDS_FILE, []);
}
export async function saveWorlds(w: WorldData[]) {
  await writeJson(WORLDS_FILE, w); return w;
}

export async function readPlaces(): Promise<Place[]> {
  return readJson<Place[]>(PLACES_FILE, []);
}
export async function savePlaces(p: Place[]) {
  await writeJson(PLACES_FILE, p); return p;
}

export async function readLorebooks(): Promise<LorebookEntry[]> {
  return readJson<LorebookEntry[]>(LOREBOOKS_FILE, []);
}
export async function saveLorebooks(l: LorebookEntry[]) {
  await writeJson(LOREBOOKS_FILE, l); return l;
}

export async function readAssets(): Promise<Asset[]> {
  return readJson<Asset[]>(ASSETS_FILE, []);
}
export async function saveAssets(a: Asset[]) {
  await writeJson(ASSETS_FILE, a); return a;
}

// ── Collision Check ──────────────────────────────────────────────────────────

export async function checkSettingsCollisions(input: {
  characterIds: string[]; worldId?: string; lorebookIds: string[];
}) {
  const [characters, worlds, lorebooks] = await Promise.all([
    (async () => {
      try { const { readBotConfig } = await import("@/lib/bot-config");
        return (await readBotConfig()).characters.filter((c: { id: string }) => input.characterIds.includes(c.id));
      } catch { return []; }
    })(),
    readWorlds(), readLorebooks(),
  ]);

  const collisions: CollisionResult[] = [];
  const world = input.worldId ? worlds.find((w: WorldData) => w.id === input.worldId) : undefined;
  const selLbs = lorebooks.filter((l: LorebookEntry) => input.lorebookIds.includes(l.id));

  for (const char of characters as Array<{ id: string; name: string }>) {
    const overlap = new Map<string, number>();
    for (const lb of selLbs.filter((l: LorebookEntry) => l.characterIds.includes(char.id) || !l.characterIds.length)) {
      for (const kw of lb.keywords) { overlap.set(kw, (overlap.get(kw) ?? 0) + 1); }
    }
    for (const [kw, count] of overlap) {
      if (count > 1) collisions.push({ type: "lorebook_overlap", source: `Character: ${char.name}`, target: `Keyword "${kw}"`, description: `키워드 "${kw}"가 ${count}개 로어북에서 중복 호출될 수 있습니다.` });
    }
  }
  if (world && characters.length > 0) {
    for (const char of characters as Array<{ id: string; name: string }>) {
      if (world.characters && !world.characters.includes(char.name))
        collisions.push({ type: "world_character", source: `World: ${world.name}`, target: `Character: ${char.name}`, description: `${char.name}이(가) 세계관 등장인물 목록에 없습니다.` });
    }
  }
  return collisions;
}

// ── Lorebook Test ────────────────────────────────────────────────────────────

export async function testLorebookActivation(text: string) {
  const lbs = await readLorebooks();
  const active = lbs.filter((l: LorebookEntry) => l.isActive);
  const results: Array<{ entry: LorebookEntry; matchedKeywords: string[]; matchCount: number }> = [];
  const lowerText = text.toLowerCase();

  for (const entry of active) {
    const matched = entry.keywords.filter((kw: string) => lowerText.includes(kw.toLowerCase()));
    if (matched.length) results.push({ entry, matchedKeywords: matched, matchCount: matched.length });
  }
  results.sort((a, b) => b.matchCount - a.matchCount);

  const warnings: string[] = [];
  const overloaded = results.filter((r) => r.matchCount > 3);
  if (overloaded.length) warnings.push(`${overloaded.length}개의 로어북이 과다 호출될 수 있습니다.`);

  const dupCheck = new Map<string, number>();
  for (const r of results) for (const kw of r.matchedKeywords) dupCheck.set(kw, (dupCheck.get(kw) ?? 0) + 1);
  for (const [kw, count] of dupCheck) { if (count > 1) warnings.push(`키워드 "${kw}"가 ${count}개 로어북에서 중복 매칭됩니다.`); }

  return { results, warnings };
}
