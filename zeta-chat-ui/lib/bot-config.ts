import { characters as defaultCharacters, chatModels } from "@/lib/mock-data";
import {
  getDataPath,
  readJsonFile,
  withFileLock,
  writeJsonFile,
} from "@/lib/server-files";
import type {
  BotConfig,
  Character,
  ChatModel,
  ChatProvider,
} from "@/types/chat";

const BOT_CONFIG_FILE_NAME = "chatbots.json";

export function getBotConfigPath() {
  return getDataPath(BOT_CONFIG_FILE_NAME);
}

export function getDefaultBotConfig(): BotConfig {
  return {
    models: chatModels.map((model) => ({
      ...model,
      apiName:
        model.id === "gemma4-4b"
          ? (getConfiguredDefaultModel() ?? model.apiName)
          : model.apiName,
    })),
    characters: defaultCharacters,
    defaultCharacterId: defaultCharacters[0]?.id ?? "zeta",
  };
}

export async function readBotConfig(): Promise<BotConfig> {
  return normalizeBotConfig(
    await readJsonFile<unknown>(getBotConfigPath(), getDefaultBotConfig()),
  );
}

export async function saveBotConfig(input: unknown): Promise<BotConfig> {
  const config = normalizeBotConfig(input);
  const filePath = getBotConfigPath();
  await withFileLock(filePath, async () => {
    await writeJsonFile(filePath, config);
  });

  return config;
}

export async function resolveModelApiName(modelId: string | undefined) {
  const model = await resolveChatModel(modelId);
  return model.apiName;
}

export async function resolveChatModel(modelId: string | undefined) {
  const config = await readBotConfig();
  const requestedModelId = safeId(modelId);
  const model = config.models.find((item) => item.id === requestedModelId);
  if (model) {
    return model;
  }

  const configuredDefaultModel = getConfiguredDefaultModel();
  if (configuredDefaultModel) {
    const provider = getConfiguredDefaultProvider();
    return {
      id: safeId(`${provider}-${configuredDefaultModel}`) || "configured-model",
      label: configuredDefaultModel,
      apiName: configuredDefaultModel,
      provider,
      description: "Configured default model",
    } satisfies ChatModel;
  }

  const modelHint = requestedModelId
    ? ` for character model "${requestedModelId}"`
    : "";
  throw new Error(
    `No chat model is configured${modelHint}. Set LM_STUDIO_MODEL or OLLAMA_MODEL, or update the character model in /admin.`,
  );
}

function getConfiguredDefaultModel() {
  const provider = getConfiguredDefaultProvider();
  if (provider === "openai") {
    return (
      process.env.OPENAI_MODEL?.trim() ||
      process.env.LM_STUDIO_MODEL?.trim() ||
      process.env.OLLAMA_MODEL?.trim()
    );
  }

  if (provider === "ollama") {
    return (
      process.env.OLLAMA_MODEL?.trim() || process.env.LM_STUDIO_MODEL?.trim()
    );
  }

  return (
    process.env.LM_STUDIO_MODEL?.trim() || process.env.OLLAMA_MODEL?.trim()
  );
}

function getConfiguredDefaultProvider(): ChatProvider {
  const provider = process.env.AI_PROVIDER?.trim().toLowerCase();
  if (
    provider === "openai" ||
    provider === "ollama" ||
    provider === "deepseek"
  ) {
    return provider;
  }

  return "lmstudio";
}

function normalizeBotConfig(input: unknown): BotConfig {
  const defaults = getDefaultBotConfig();

  if (!input || typeof input !== "object") {
    return defaults;
  }

  const record = input as Partial<BotConfig>;
  const models = Array.isArray(record.models)
    ? record.models.map(normalizeModel).filter(isChatModel)
    : defaults.models;
  const safeModels = mergeDefaultModels(
    models.length > 0 ? models : defaults.models,
    defaults.models,
  );
  const modelIds = new Set(safeModels.map((model) => model.id));
  const fallbackModelId =
    getConfiguredDefaultModelId(safeModels) ?? safeModels[0]?.id ?? "";

  const characters = Array.isArray(record.characters)
    ? record.characters
        .map((character) =>
          normalizeCharacter(character, modelIds, fallbackModelId),
        )
        .filter(isCharacter)
    : defaults.characters;
  const safeCharacters =
    characters.length > 0 ? characters : defaults.characters;
  const defaultCharacterId =
    typeof record.defaultCharacterId === "string" &&
    safeCharacters.some(
      (character) => character.id === record.defaultCharacterId,
    )
      ? record.defaultCharacterId
      : safeCharacters[0].id;

  return {
    models: safeModels,
    characters: safeCharacters,
    defaultCharacterId,
  };
}

function isChatModel(value: ChatModel | null): value is ChatModel {
  return value !== null;
}

function mergeDefaultModels(models: ChatModel[], defaults: ChatModel[]) {
  const modelIds = new Set(models.map((model) => model.id));
  return [...models, ...defaults.filter((model) => !modelIds.has(model.id))];
}

function isCharacter(value: Character | null): value is Character {
  return value !== null;
}

function normalizeModel(input: unknown): ChatModel | null {
  if (!input || typeof input !== "object") {
    return null;
  }

  const record = input as Partial<ChatModel>;
  const id = safeId(record.id);
  const label = normalizeText(record.label);
  const apiName = normalizeText(record.apiName);
  const provider = normalizeProvider(record.provider);

  if (!id || !label || !apiName) {
    return null;
  }

  return {
    id,
    label,
    apiName,
    provider,
    description: normalizeText(record.description),
  };
}

function normalizeCharacter(
  input: unknown,
  modelIds: Set<string>,
  fallbackModelId: string,
): Character | null {
  if (!input || typeof input !== "object") {
    return null;
  }

  const record = input as Partial<Character>;
  const id = safeId(record.id);
  const name = normalizeText(record.name);

  if (!id || !name) {
    return null;
  }

  const requestedModelId = safeId(record.modelId);

  return {
    id,
    name,
    avatar: normalizeText(record.avatar).slice(0, 2) || name.slice(0, 1),
    avatarImageUrl: normalizeUrl(record.avatarImageUrl),
    coverGradient:
      normalizeText(record.coverGradient) ||
      "from-slate-500 via-zinc-500 to-neutral-500",
    intro: normalizeText(record.intro),
    tags: Array.isArray(record.tags)
      ? record.tags.map(normalizeText).filter(Boolean).slice(0, 8)
      : [],
    firstScene:
      normalizeText(record.firstScene) ||
      "안녕하세요. 편하게 말을 걸어 주세요.",
    personaSummary: normalizeText(record.personaSummary),
    modelId: modelIds.has(requestedModelId)
      ? requestedModelId
      : requestedModelId || fallbackModelId,
  };
}

function getConfiguredDefaultModelId(models: ChatModel[]) {
  const configuredDefaultModel = getConfiguredDefaultModel();
  if (!configuredDefaultModel) {
    return undefined;
  }

  return models.find((model) => model.apiName === configuredDefaultModel)?.id;
}

function normalizeText(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function safeId(value: unknown) {
  if (typeof value !== "string") {
    return "";
  }

  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function normalizeProvider(value: unknown): ChatProvider {
  if (
    value === "lmstudio" ||
    value === "ollama" ||
    value === "openai" ||
    value === "deepseek"
  ) {
    return value;
  }

  return getConfiguredDefaultProvider();
}

function normalizeUrl(value: unknown) {
  const text = normalizeText(value);
  if (!text) {
    return undefined;
  }

  try {
    const url = new URL(text);
    return url.protocol === "http:" || url.protocol === "https:"
      ? url.toString()
      : undefined;
  } catch {
    return undefined;
  }
}
