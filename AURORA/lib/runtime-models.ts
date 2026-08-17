import type { RuntimeModel } from "@/types/chat";

type LmStudioModelsResponse = {
  data?: Array<{
    id?: unknown;
    owned_by?: unknown;
  }>;
};

type OllamaModelsResponse = {
  models?: Array<{
    name?: unknown;
    model?: unknown;
    size?: unknown;
    modified_at?: unknown;
  }>;
};

type ModelsCacheEntry = {
  expiresAt: number;
  models: RuntimeModel[];
};

export const DEFAULT_LM_STUDIO_BASE_URL = "http://localhost:1234/v1";
export const DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434";
export const DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1";
export const DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1";
export const FALLBACK_LM_STUDIO_MODEL = "local-model";
export const FALLBACK_OLLAMA_MODEL = "qwen2.5:7b";
export const DEEPSEEK_FLASH_MODEL = "deepseek-v4-flash";

const modelsCache = new Map<string, ModelsCacheEntry>();

export function getLmStudioBaseUrl() {
  return normalizeBaseUrl(
    process.env.LM_STUDIO_BASE_URL?.trim() ||
      process.env.CHAT_PROVIDER_BASE_URL?.trim() ||
      DEFAULT_LM_STUDIO_BASE_URL,
  );
}

export function getOpenAiBaseUrl() {
  return normalizeBaseUrl(
    process.env.OPENAI_BASE_URL?.trim() || DEFAULT_OPENAI_BASE_URL,
  );
}

export function getDeepSeekBaseUrl() {
  return normalizeBaseUrl(
    process.env.DEEPSEEK_BASE_URL?.trim() || DEFAULT_DEEPSEEK_BASE_URL,
  );
}

export function getOllamaBaseUrl() {
  return normalizeBaseUrl(
    process.env.OLLAMA_BASE_URL?.trim() ||
      process.env.CHAT_PROVIDER_BASE_URL?.trim() ||
      DEFAULT_OLLAMA_BASE_URL,
  );
}

export async function fetchLmStudioModels(
  baseUrl = getLmStudioBaseUrl(),
  timeoutMs = getNumberEnv("LM_STUDIO_MODELS_TIMEOUT_MS", 5000),
) {
  const cachedModels = getCachedModels("lmstudio", baseUrl);
  if (cachedModels) {
    return cachedModels;
  }

  const response = await fetch(`${baseUrl}/models`, {
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `LM Studio models API error (${response.status}): ${detail.slice(0, 160)}`,
    );
  }

  const payload = (await response.json()) as LmStudioModelsResponse;
  const models = normalizeLmStudioModels(payload);
  setCachedModels("lmstudio", baseUrl, models);
  return models;
}

export async function fetchOllamaModels(
  baseUrl = getOllamaBaseUrl(),
  timeoutMs = getNumberEnv("OLLAMA_MODELS_TIMEOUT_MS", 5000),
) {
  const cachedModels = getCachedModels("ollama", baseUrl);
  if (cachedModels) {
    return cachedModels;
  }

  const response = await fetch(`${baseUrl}/api/tags`, {
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Ollama models API error (${response.status}): ${detail.slice(0, 160)}`,
    );
  }

  const payload = (await response.json()) as OllamaModelsResponse;
  const models = normalizeOllamaModels(payload);
  setCachedModels("ollama", baseUrl, models);
  return models;
}

export async function resolveLmStudioDefaultModel() {
  const configuredModel = process.env.LM_STUDIO_MODEL?.trim();
  if (configuredModel) {
    return configuredModel;
  }

  try {
    const models = await fetchLmStudioModels();
    const detectedNames = models.map((model) => model.apiName);
    return chooseDetectedModel(detectedNames, configuredModel);
  } catch {
    return configuredModel || FALLBACK_LM_STUDIO_MODEL;
  }
}

export async function resolveOllamaDefaultModel() {
  const configuredModel = process.env.OLLAMA_MODEL?.trim();
  if (configuredModel) {
    return configuredModel;
  }

  try {
    const models = await fetchOllamaModels();
    const detectedNames = models.map((model) => model.apiName);
    return chooseDetectedModel(
      detectedNames,
      configuredModel,
      FALLBACK_OLLAMA_MODEL,
    );
  } catch {
    return configuredModel || FALLBACK_OLLAMA_MODEL;
  }
}

export async function resolveLmStudioRuntimeModel(selectedModel?: string) {
  const requestedModel = selectedModel?.trim();
  const configuredModel = process.env.LM_STUDIO_MODEL?.trim();
  const fallbackModel = configuredModel || requestedModel || FALLBACK_LM_STUDIO_MODEL;

  if (requestedModel || configuredModel) {
    return {
      model: requestedModel || fallbackModel,
      fallbackModel,
    };
  }

  try {
    const models = await fetchLmStudioModels();
    const detectedNames = models.map((model) => model.apiName);
    const detectedFallbackModel = chooseDetectedModel(
      detectedNames,
      configuredModel,
    );

    return {
      model: detectedFallbackModel,
      fallbackModel: detectedFallbackModel,
    };
  } catch {
    return {
      model: fallbackModel,
      fallbackModel,
    };
  }
}

export async function resolveOllamaRuntimeModel(selectedModel?: string) {
  const requestedModel = selectedModel?.trim();
  const configuredModel = process.env.OLLAMA_MODEL?.trim();
  const fallbackModel = configuredModel || requestedModel || FALLBACK_OLLAMA_MODEL;

  if (requestedModel || configuredModel) {
    return {
      model: requestedModel || fallbackModel,
      fallbackModel,
    };
  }

  try {
    const models = await fetchOllamaModels();
    const detectedNames = models.map((model) => model.apiName);
    const detectedFallbackModel = chooseDetectedModel(
      detectedNames,
      configuredModel,
      FALLBACK_OLLAMA_MODEL,
    );

    return {
      model: detectedFallbackModel,
      fallbackModel: detectedFallbackModel,
    };
  } catch {
    return {
      model: fallbackModel,
      fallbackModel,
    };
  }
}

export function chooseDetectedModel(
  detectedNames: string[],
  preferredModel = process.env.LM_STUDIO_MODEL?.trim(),
  fallbackModel = FALLBACK_LM_STUDIO_MODEL,
) {
  if (preferredModel && detectedNames.includes(preferredModel)) {
    return preferredModel;
  }

  return detectedNames[0] ?? preferredModel ?? fallbackModel;
}

function normalizeLmStudioModels(payload: LmStudioModelsResponse): RuntimeModel[] {
  const seen = new Set<string>();
  const models: RuntimeModel[] = [];

  for (const item of payload.data ?? []) {
    const apiName = typeof item.id === "string" ? item.id.trim() : "";
    if (!apiName || seen.has(apiName)) {
      continue;
    }

    seen.add(apiName);
    models.push({
      id: `lmstudio:${apiName}`,
      label: apiName,
      apiName,
      provider: "lmstudio",
      description:
        typeof item.owned_by === "string" && item.owned_by.trim()
          ? `Owner: ${item.owned_by.trim()}`
          : "Detected from LM Studio",
      source: "lmstudio",
    });
  }

  return models.sort((left, right) => left.label.localeCompare(right.label));
}

function normalizeOllamaModels(payload: OllamaModelsResponse): RuntimeModel[] {
  const seen = new Set<string>();
  const models: RuntimeModel[] = [];

  for (const item of payload.models ?? []) {
    const apiName =
      typeof item.name === "string" && item.name.trim()
        ? item.name.trim()
        : typeof item.model === "string"
          ? item.model.trim()
          : "";
    if (!apiName || seen.has(apiName)) {
      continue;
    }

    seen.add(apiName);
    models.push({
      id: `ollama:${apiName}`,
      label: apiName,
      apiName,
      provider: "ollama",
      description:
        typeof item.size === "number" && Number.isFinite(item.size)
          ? `Ollama local model, ${formatBytes(item.size)}`
          : "Detected from Ollama",
      source: "ollama",
    });
  }

  return models.sort((left, right) => left.label.localeCompare(right.label));
}

function getCachedModels(provider: "lmstudio" | "ollama", baseUrl: string) {
  const cacheMs = getModelsCacheMs(provider);
  if (cacheMs === 0) {
    return undefined;
  }

  const cacheKey = `${provider}:${baseUrl}`;
  const cacheEntry = modelsCache.get(cacheKey);
  if (!cacheEntry || cacheEntry.expiresAt <= Date.now()) {
    modelsCache.delete(cacheKey);
    return undefined;
  }

  return cacheEntry.models;
}

function setCachedModels(
  provider: "lmstudio" | "ollama",
  baseUrl: string,
  models: RuntimeModel[],
) {
  const cacheMs = getModelsCacheMs(provider);
  if (cacheMs === 0) {
    return;
  }

  modelsCache.set(`${provider}:${baseUrl}`, {
    expiresAt: Date.now() + cacheMs,
    models,
  });
}

function getModelsCacheMs(provider: "lmstudio" | "ollama") {
  const envName =
    provider === "lmstudio"
      ? "LM_STUDIO_MODELS_CACHE_MS"
      : "OLLAMA_MODELS_CACHE_MS";
  return getNonNegativeNumberEnv(envName, 30_000);
}

export function normalizeBaseUrl(baseUrl: string) {
  const trimmed = baseUrl.trim();
  const withProtocol = /^https?:\/\//i.test(trimmed)
    ? trimmed
    : `http://${trimmed}`;

  return withProtocol.replace(/\/+$/, "");
}

export function getProviderReachabilityHint(baseUrl: string) {
  try {
    const url = new URL(baseUrl);
    const host = url.hostname.toLowerCase();
    const isLoopback =
      host === "localhost" ||
      host === "127.0.0.1" ||
      host === "::1" ||
      host === "[::1]";

    if (isLoopback) {
      return "The configured provider uses a loopback address. On the deployed Raspberry Pi server, that only works when the provider runs on the same Raspberry Pi. If Ollama or LM Studio runs on another machine, set OLLAMA_BASE_URL, LM_STUDIO_BASE_URL, or CHAT_PROVIDER_BASE_URL to that machine's reachable LAN URL.";
    }

    return `The configured provider host is ${url.host}. Confirm that the Raspberry Pi can reach it and that the provider allows connections from the server.`;
  } catch {
    return "Check OLLAMA_BASE_URL, LM_STUDIO_BASE_URL, or CHAT_PROVIDER_BASE_URL. It must be a reachable HTTP(S) base URL for the selected provider.";
  }
}

function formatBytes(bytes: number) {
  const gib = bytes / 1024 ** 3;
  if (gib >= 1) {
    return `${gib.toFixed(1)} GB`;
  }

  return `${(bytes / 1024 ** 2).toFixed(0)} MB`;
}

function getNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function getNonNegativeNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}
