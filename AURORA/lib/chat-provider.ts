import { resolveChatModel } from "@/lib/bot-config";
import { getDeepSeekApiKey } from "@/lib/provider-settings";
import {
  DEEPSEEK_FLASH_MODEL,
  getDeepSeekBaseUrl,
  getLmStudioBaseUrl,
  getOllamaBaseUrl,
  getOpenAiBaseUrl,
  getProviderReachabilityHint,
  resolveLmStudioDefaultModel,
  resolveLmStudioRuntimeModel,
  resolveOllamaRuntimeModel,
} from "@/lib/runtime-models";
import type { OpenAIMessage } from "@/lib/chat-prompts";
import type { ModelSelection } from "@/types/chat";

export type ChatCompletionChoice = {
  delta?: {
    content?: string | null;
  };
  message?: {
    content?: string | null;
  };
};

export type ChatCompletionResponse = {
  choices?: ChatCompletionChoice[];
  message?: {
    content?: string | null;
  };
};

type OllamaChatStreamResponse = {
  message?: {
    content?: string | null;
  };
  done?: boolean;
};

export type ChatCompletionConfig = {
  baseUrl: string;
  apiKey?: string;
  maxTokens: number;
  model: string;
  fallbackModel: string;
  provider: ModelSelection["provider"];
  messages: OpenAIMessage[];
};

export type ModelResult = {
  requestedModel: ModelSelection;
  usedModel: ModelSelection;
  fallbackModel: ModelSelection;
  usedFallbackModel: boolean;
};

export async function getProviderRuntime(
  modelId: string,
  modelSelection?: ModelSelection,
) {
  const provider = process.env.AI_PROVIDER?.trim().toLowerCase();
  const selectedModel = modelSelection?.model.trim();
  const characterModel = selectedModel
    ? undefined
    : await resolveChatModel(modelId);
  const selectedProvider =
    modelSelection?.provider ?? characterModel?.provider ?? provider;
  const useOpenAi = selectedProvider === "openai";
  const useDeepSeek = selectedProvider === "deepseek";
  const useOllama = selectedProvider === "ollama";
  const baseUrl = useDeepSeek
    ? getDeepSeekBaseUrl()
    : useOpenAi
      ? getOpenAiBaseUrl()
      : useOllama
        ? getOllamaBaseUrl()
        : getLmStudioBaseUrl();
  const apiKey = useDeepSeek
    ? await getDeepSeekApiKey()
    : useOpenAi
      ? process.env.OPENAI_API_KEY
      : useOllama
        ? undefined
        : process.env.LM_STUDIO_API_KEY ?? process.env.OPENAI_API_KEY;
  if (useDeepSeek && !apiKey) {
    throw new Error(
      "DeepSeek API key is not configured. Enter it in /admin and save the chatbot settings.",
    );
  }
  const runtimeModel = useOllama
    ? await resolveOllamaRuntimeModel(selectedModel || characterModel?.apiName)
    : useDeepSeek
      ? {
          model: selectedModel || characterModel?.apiName || DEEPSEEK_FLASH_MODEL,
          fallbackModel: characterModel?.apiName || DEEPSEEK_FLASH_MODEL,
        }
      : useOpenAi
        ? {
            model:
              selectedModel ||
              process.env.OPENAI_MODEL ||
              characterModel?.apiName ||
              (await resolveLmStudioDefaultModel()),
            fallbackModel:
              process.env.OPENAI_MODEL ||
              characterModel?.apiName ||
              (await resolveLmStudioDefaultModel()),
          }
        : await resolveLmStudioRuntimeModel(
            selectedModel || characterModel?.apiName,
          );

  return {
    baseUrl,
    apiKey,
    model: runtimeModel.model,
    fallbackModel: runtimeModel.fallbackModel,
    provider: useOpenAi
      ? ("openai" as const)
      : useDeepSeek
        ? ("deepseek" as const)
        : useOllama
          ? ("ollama" as const)
          : ("lmstudio" as const),
  };
}

export async function fetchChatCompletion(
  baseUrl: string,
  body: {
    apiKey?: string;
    provider: ModelSelection["provider"];
    model: string;
    messages: OpenAIMessage[];
    maxTokens: number;
    stream: boolean;
    temperature?: number;
    timeoutMs?: number;
    signal?: AbortSignal;
  },
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (body.apiKey) {
    headers.Authorization = `Bearer ${body.apiKey}`;
  }

  try {
    const endpoint =
      body.provider === "ollama"
        ? `${baseUrl}/api/chat`
        : `${baseUrl}/chat/completions`;
    const payload =
      body.provider === "ollama"
        ? {
            model: body.model,
            messages: body.messages,
            stream: body.stream,
            think: getBooleanEnv("OLLAMA_THINK", false),
            keep_alive: process.env.OLLAMA_KEEP_ALIVE?.trim() || "10m",
            options: {
              temperature: body.temperature ?? 0.8,
              num_predict: body.maxTokens,
              num_ctx: getNumberEnv("OLLAMA_NUM_CTX", 4096),
              ...(process.env.OLLAMA_NUM_GPU
                ? { num_gpu: getNumberEnv("OLLAMA_NUM_GPU", 99) }
                : {}),
            },
          }
        : {
            model: body.model,
            messages: body.messages,
            max_tokens: body.maxTokens,
            stream: body.stream,
            temperature: body.temperature ?? 0.8,
          };

    return await fetch(endpoint, {
      method: "POST",
      headers,
      signal: createAbortSignal(
        body.timeoutMs ?? getNumberEnv("CHAT_COMPLETION_TIMEOUT_MS", 120_000),
        body.signal,
      ),
      body: JSON.stringify(payload),
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw new Error("Chat request was aborted before completion.");
    }

    const hint = getProviderReachabilityHint(baseUrl);
    throw new Error(
      `Cannot connect to the chat API at ${baseUrl}. Check that the provider is reachable from the Next.js server. ${hint}`,
    );
  }
}

export async function fetchChatCompletionWithFallback(
  config: ChatCompletionConfig,
  stream: boolean,
  signal?: AbortSignal,
): Promise<{ response: Response; modelResult: ModelResult }> {
  const modelResult: ModelResult = {
    requestedModel: {
      provider: config.provider,
      model: config.model,
    },
    usedModel: {
      provider: config.provider,
      model: config.model,
    },
    fallbackModel: {
      provider: config.provider,
      model: config.fallbackModel,
    },
    usedFallbackModel: false,
  };

  try {
    const response = await fetchChatCompletion(config.baseUrl, {
      apiKey: config.apiKey,
      provider: config.provider,
      model: config.model,
      messages: config.messages,
      maxTokens: config.maxTokens,
      stream,
      signal,
    });

    if (response.ok || config.model === config.fallbackModel) {
      return { response, modelResult };
    }

    await response.body?.cancel().catch(() => undefined);
    const fallbackResponse = await fetchChatCompletion(config.baseUrl, {
      apiKey: config.apiKey,
      provider: config.provider,
      model: config.fallbackModel,
      messages: config.messages,
      maxTokens: config.maxTokens,
      stream,
      signal,
    });

    if (fallbackResponse.ok) {
      modelResult.usedModel = modelResult.fallbackModel;
      modelResult.usedFallbackModel = true;
      return { response: fallbackResponse, modelResult };
    }

    return { response: fallbackResponse, modelResult };
  } catch (error) {
    if (config.model === config.fallbackModel) {
      throw error;
    }

    const fallbackResponse = await fetchChatCompletion(config.baseUrl, {
      apiKey: config.apiKey,
      provider: config.provider,
      model: config.fallbackModel,
      messages: config.messages,
      maxTokens: config.maxTokens,
      stream,
      signal,
    });
    modelResult.usedModel = modelResult.fallbackModel;
    modelResult.usedFallbackModel = true;
    return { response: fallbackResponse, modelResult };
  }
}

export async function* readCompletionStream(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() ?? "";

      for (const event of events) {
        const content = parseStreamEvent(event);
        if (content !== null) {
          yield content;
        }
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      const content = parseStreamEvent(buffer);
      if (content !== null) {
        yield content;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function* readOllamaStream(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const content = parseOllamaStreamLine(line);
        if (content !== null) {
          yield content;
        }
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      const content = parseOllamaStreamLine(buffer);
      if (content !== null) {
        yield content;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function getCompletionContent(payload: ChatCompletionResponse) {
  return (
    payload.choices
      ?.map((choice) => choice.delta?.content ?? choice.message?.content ?? "")
      .join("") ??
    payload.message?.content ??
    ""
  );
}

function parseStreamEvent(event: string) {
  const data = event
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n")
    .trim();

  if (!data || data === "[DONE]") {
    return null;
  }

  try {
    const payload = JSON.parse(data) as ChatCompletionResponse;
    return getCompletionContent(payload);
  } catch {
    return data;
  }
}

function parseOllamaStreamLine(line: string) {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const payload = JSON.parse(trimmed) as OllamaChatStreamResponse;
    return payload.done ? null : payload.message?.content ?? "";
  } catch {
    return null;
  }
}

function createAbortSignal(timeoutMs: number | undefined, signal?: AbortSignal) {
  const signals = [
    signal,
    timeoutMs && timeoutMs > 0 ? AbortSignal.timeout(timeoutMs) : undefined,
  ].filter((item): item is AbortSignal => Boolean(item));

  if (signals.length === 0) {
    return undefined;
  }

  if (signals.length === 1) {
    return signals[0];
  }

  return AbortSignal.any(signals);
}

function isAbortError(error: unknown) {
  return (
    error instanceof DOMException && error.name === "AbortError"
  ) || (error instanceof Error && error.name === "AbortError");
}

function getNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function getBooleanEnv(name: string, fallback: boolean) {
  const value = process.env[name]?.trim().toLowerCase();
  if (value === "1" || value === "true" || value === "yes") {
    return true;
  }
  if (value === "0" || value === "false" || value === "no") {
    return false;
  }
  return fallback;
}
