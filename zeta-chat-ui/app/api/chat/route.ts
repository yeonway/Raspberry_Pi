import { NextResponse } from "next/server";
import {
  appendMemoryTurn,
  applyMemoryUpdate,
  buildMemoryContext,
  readMemoryState,
  type MemoryTurn,
} from "@/lib/chat-memory";
import {
  buildMemoryUpdatePrompt,
  parseMemoryUpdate,
} from "@/lib/chat-memory-extraction";
import { appendChatLog } from "@/lib/chat-logs";
import { getCurrentUser } from "@/lib/auth";
import {
  createLogEntry,
  getTurnUserContent,
  persistSuccessfulTurn,
} from "@/lib/chat-persistence";
import {
  fetchChatCompletion,
  fetchChatCompletionWithFallback,
  getCompletionContent,
  getProviderRuntime,
  readCompletionStream,
  readOllamaStream,
  type ChatCompletionConfig,
  type ChatCompletionResponse,
} from "@/lib/chat-provider";
import { buildLmStudioMessages } from "@/lib/chat-prompts";
import { parseChatRequest, type ParsedChatRequest } from "@/lib/chat-request";
import { getRateLimitError } from "@/lib/rate-limit";
import {
  createResponseStreamLimiter,
  getResponseMaxTokens,
  normalizeResponseContent,
} from "@/lib/chat-response";
import type {
  AuthUser,
  Character,
  ChatTurnAction,
  Message,
} from "@/types/chat";

type ChatPerfTrace = {
  requestId: string;
  startedAtMs: number;
  firstTokenLogged: boolean;
  outputChars: number;
};

const STREAM_DELAY_MS = getNonNegativeNumberEnv("STREAM_TOKEN_DELAY_MS", 0);
const STREAM_ENCODER = new TextEncoder();
const DEFAULT_MEMORY_IDLE_UPDATE_MS = 5 * 60 * 1000;

type MemoryUpdateKey = {
  sessionId: string;
  chatId: string;
  characterId: string;
};

type QueuedMemoryUpdate = {
  character: Character;
  flushing: boolean;
  key: MemoryUpdateKey;
  timer: ReturnType<typeof setTimeout> | null;
  turns: MemoryTurn[];
};

const memoryUpdateQueue = new Map<string, QueuedMemoryUpdate>();

export const runtime = "nodejs";

export async function POST(request: Request) {
  const rateLimitError = getRateLimitError(request, {
    keyPrefix: "chat",
    maxRequests: getNonNegativeNumberEnv("CHAT_RATE_LIMIT_MAX", 30),
    windowMs: getNonNegativeNumberEnv("CHAT_RATE_LIMIT_WINDOW_MS", 60_000),
  });
  if (rateLimitError) {
    return rateLimitError;
  }

  let parsed: ParsedChatRequest | null = null;
  let perfTrace: ChatPerfTrace | null = null;
  const user = await getCurrentUser(request);

  try {
    const body = await request.json();
    parsed = parseChatRequest(body);
    perfTrace = createChatPerfTrace();
    logChatPerf(perfTrace, "request_parsed", getParsedPerfFields(parsed, user));

    if (parsed.stream) {
      return createStreamingChatResponse(
        parsed,
        user,
        request.signal,
        perfTrace,
      );
    }

    const result = await createChatCompletion(parsed, user, perfTrace, {
      stream: false,
      signal: request.signal,
    });
    const memoryItem = await persistSuccessfulTurn(
      user,
      parsed,
      result.content,
    );
    await appendChatLog(
      createLogEntry(parsed, {
        assistantContent: result.content,
        modelResult: result.modelResult,
        user,
      }),
    );

    void updateChatMemory(parsed, user, result.content).catch(() => undefined);

    logChatPerf(perfTrace, "request_complete", {
      outputChars: result.content.length,
    });
    return NextResponse.json({ content: result.content, memoryItem });
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Chat response generation failed.";
    if (perfTrace) {
      logChatPerf(perfTrace, "request_error", { error: message.slice(0, 240) });
    }

    if (parsed) {
      await appendChatLog(
        createLogEntry(parsed, { error: message, user }),
      ).catch(() => undefined);
    }

    return NextResponse.json({ error: message }, { status: 500 });
  }
}

function createChatPerfTrace(): ChatPerfTrace {
  return {
    requestId: crypto.randomUUID().slice(0, 8),
    startedAtMs: performance.now(),
    firstTokenLogged: false,
    outputChars: 0,
  };
}

function logChatPerf(
  trace: ChatPerfTrace,
  event: string,
  fields: Record<string, unknown> = {},
) {
  console.info(
    "[chat-perf]",
    JSON.stringify({
      event,
      requestId: trace.requestId,
      elapsedMs: elapsedSince(trace.startedAtMs),
      ...fields,
    }),
  );
}

function logFirstTokenIfNeeded(trace: ChatPerfTrace, chars: number) {
  if (trace.firstTokenLogged || chars <= 0) {
    return;
  }

  trace.firstTokenLogged = true;
  logChatPerf(trace, "first_token", {
    firstTokenMs: elapsedSince(trace.startedAtMs),
  });
}

function elapsedSince(startMs: number) {
  return Math.round(performance.now() - startMs);
}

function getParsedPerfFields(parsed: ParsedChatRequest, user: AuthUser | null) {
  return {
    characterId: parsed.character.id,
    hasUser: Boolean(user),
    inputMessages: parsed.messages.length,
    requestedProvider: parsed.modelSelection?.provider,
    requestedModel: parsed.modelSelection?.model,
    responseFlavor: parsed.responseStyle.flavor,
    responseLength: parsed.responseStyle.length,
    stream: parsed.stream,
    turnAction: parsed.turnAction,
  };
}

function getConfigPerfFields(config: ChatCompletionConfig) {
  return {
    fallbackModel: config.fallbackModel,
    maxTokens: config.maxTokens,
    model: config.model,
    promptChars: config.messages.reduce(
      (total, message) => total + message.content.length,
      0,
    ),
    promptMessages: config.messages.length,
    provider: config.provider,
  };
}

async function createChatCompletion(
  parsed: ParsedChatRequest,
  user: AuthUser | null,
  perfTrace: ChatPerfTrace,
  options: { stream: false; signal?: AbortSignal },
) {
  const configStartMs = performance.now();
  logChatPerf(perfTrace, "config_start");
  const config = await buildChatCompletionConfig(parsed, user);
  logChatPerf(perfTrace, "config_ready", {
    configMs: elapsedSince(configStartMs),
    ...getConfigPerfFields(config),
  });
  const providerStartMs = performance.now();
  logChatPerf(perfTrace, "provider_fetch_start", {
    provider: config.provider,
    model: config.model,
    stream: options.stream,
  });
  const result = await fetchChatCompletionWithFallback(
    config,
    options.stream,
    options.signal,
  );
  const response = result.response;
  logChatPerf(perfTrace, "provider_headers", {
    providerMs: elapsedSince(providerStartMs),
    status: response.status,
    usedFallbackModel: result.modelResult.usedFallbackModel,
    usedModel: result.modelResult.usedModel.model,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Chat API error (${response.status}): ${detail.slice(0, 240)}`,
    );
  }

  const payload = (await response.json()) as ChatCompletionResponse;
  const content = normalizeResponseContent(
    getCompletionContent(payload),
    parsed.responseStyle,
  );
  logFirstTokenIfNeeded(perfTrace, content.length);

  if (!content) {
    throw new Error("Chat API returned an empty response.");
  }

  return {
    content,
    modelResult: result.modelResult,
  };
}

async function buildChatCompletionConfig(
  {
    chatId,
    sessionId,
    character,
    customCharacterPrompt,
    messages,
    modelSelection,
    responseStyle,
    turnAction,
  }: ParsedChatRequest,
  user: AuthUser | null,
): Promise<ChatCompletionConfig> {
  const sessionKey = user?.id ?? sessionId;
  const [runtimeConfig, memoryContext] = await Promise.all([
    getProviderRuntime(character.modelId, modelSelection),
    buildMemoryContext({
      sessionId: sessionKey,
      chatId,
      character,
      query: getTurnUserContent(messages, turnAction),
    }),
  ]);

  return {
    ...runtimeConfig,
    maxTokens: getResponseMaxTokens(responseStyle),
    messages: await buildLmStudioMessages(
      character,
      user,
      customCharacterPrompt,
      messages,
      responseStyle,
      memoryContext,
      turnAction,
    ),
  };
}

function createStreamingChatResponse(
  parsed: ParsedChatRequest,
  user: AuthUser | null,
  signal?: AbortSignal,
  perfTrace?: ChatPerfTrace,
) {
  let streamCancelled = false;
  let upstreamAbortController: AbortController | null = null;
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let assistantContent = "";
      const trace = perfTrace ?? createChatPerfTrace();
      const providerAbortController = new AbortController();
      upstreamAbortController = providerAbortController;
      const providerSignal = signal
        ? AbortSignal.any([signal, providerAbortController.signal])
        : providerAbortController.signal;
      const responseLimiter = createResponseStreamLimiter(parsed.responseStyle);

      try {
        const configStartMs = performance.now();
        logChatPerf(trace, "config_start");
        const config = await buildChatCompletionConfig(parsed, user);
        logChatPerf(trace, "config_ready", {
          configMs: elapsedSince(configStartMs),
          ...getConfigPerfFields(config),
        });
        const providerStartMs = performance.now();
        logChatPerf(trace, "provider_fetch_start", {
          provider: config.provider,
          model: config.model,
          stream: true,
        });
        const result = await fetchChatCompletionWithFallback(
          config,
          true,
          providerSignal,
        );
        const response = result.response;
        logChatPerf(trace, "provider_headers", {
          providerMs: elapsedSince(providerStartMs),
          status: response.status,
          usedFallbackModel: result.modelResult.usedFallbackModel,
          usedModel: result.modelResult.usedModel.model,
        });

        if (!response.ok) {
          const detail = await response.text().catch(() => "");
          throw new Error(
            `Chat API error (${response.status}): ${detail.slice(0, 240)}`,
          );
        }

        const contentType = response.headers.get("content-type") ?? "";
        if (contentType.includes("text/event-stream") && response.body) {
          for await (const chunk of readCompletionStream(response.body)) {
            logFirstTokenIfNeeded(trace, chunk.length);
            const limitedChunk = responseLimiter.append(chunk);
            if (limitedChunk.text) {
              assistantContent += limitedChunk.text;
              trace.outputChars = assistantContent.length;
              await enqueueText(controller, limitedChunk.text);
            }
            if (limitedChunk.done) {
              await response.body.cancel().catch(() => undefined);
              providerAbortController.abort();
              break;
            }
          }
        } else if (config.provider === "ollama" && response.body) {
          for await (const chunk of readOllamaStream(response.body)) {
            logFirstTokenIfNeeded(trace, chunk.length);
            const limitedChunk = responseLimiter.append(chunk);
            if (limitedChunk.text) {
              assistantContent += limitedChunk.text;
              trace.outputChars = assistantContent.length;
              await enqueueText(controller, limitedChunk.text);
            }
            if (limitedChunk.done) {
              await response.body.cancel().catch(() => undefined);
              providerAbortController.abort();
              break;
            }
          }
        } else {
          const payload = (await response.json()) as ChatCompletionResponse;
          const content = normalizeResponseContent(
            getCompletionContent(payload),
            parsed.responseStyle,
          );
          if (!content) {
            throw new Error("Chat API returned an empty response.");
          }
          logFirstTokenIfNeeded(trace, content.length);
          assistantContent = content;
          trace.outputChars = content.length;
          await enqueueText(controller, content);
        }
        assistantContent = normalizeResponseContent(
          assistantContent,
          parsed.responseStyle,
        );
        trace.outputChars = assistantContent.length;
        logChatPerf(trace, "provider_stream_done", {
          outputChars: assistantContent.length,
        });

        if (!assistantContent.trim()) {
          throw new Error("Chat API returned an empty response.");
        }

        await appendChatLog(
          createLogEntry(parsed, {
            assistantContent,
            modelResult: result.modelResult,
            user,
          }),
        ).catch(() => undefined);
        const memoryItem = await persistSuccessfulTurn(
          user,
          parsed,
          assistantContent,
        ).catch(() => undefined);
        void updateChatMemory(parsed, user, assistantContent).catch(
          () => undefined,
        );
        enqueueEvent(controller, "done", { memoryItem });
        logChatPerf(trace, "request_complete", {
          outputChars: assistantContent.length,
        });
      } catch (error) {
        if (signal?.aborted || streamCancelled || providerSignal.aborted) {
          providerAbortController.abort();
          logChatPerf(trace, "request_aborted", {
            outputChars: assistantContent.length,
          });
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Chat response generation failed.";
        logChatPerf(trace, "request_error", { error: message.slice(0, 240) });

        await appendChatLog(
          createLogEntry(parsed, { error: message, user }),
        ).catch(() => undefined);
        try {
          enqueueEvent(controller, "error", { message });
        } catch {
          logChatPerf(trace, "error_event_dropped");
        }
      } finally {
        if (upstreamAbortController === providerAbortController) {
          upstreamAbortController = null;
        }
        try {
          controller.close();
        } catch {
          logChatPerf(trace, "stream_close_dropped");
        }
      }
    },
    cancel() {
      streamCancelled = true;
      upstreamAbortController?.abort();
    },
  });

  return new Response(stream, {
    headers: {
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Type": "text/event-stream; charset=utf-8",
      "X-Accel-Buffering": "no",
    },
  });
}

async function enqueueText(
  controller: ReadableStreamDefaultController<Uint8Array>,
  text: string,
) {
  for (const part of splitGraphemes(text)) {
    enqueueEvent(controller, "token", { content: part });
    if (STREAM_DELAY_MS > 0) {
      await delay(STREAM_DELAY_MS);
    }
  }
}

function enqueueEvent(
  controller: ReadableStreamDefaultController<Uint8Array>,
  event: string,
  data: unknown,
) {
  controller.enqueue(
    STREAM_ENCODER.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
  );
}

function splitGraphemes(text: string) {
  type Segment = { segment: string };
  type Segmenter = {
    segment(input: string): Iterable<Segment>;
  };
  const SegmenterCtor = (
    Intl as typeof Intl & {
      Segmenter?: new (
        locale: string,
        options: { granularity: "grapheme" },
      ) => Segmenter;
    }
  ).Segmenter;

  if (SegmenterCtor) {
    const segmenter = new SegmenterCtor("ko", { granularity: "grapheme" });
    return Array.from(segmenter.segment(text), (segment) => segment.segment);
  }

  return Array.from(text);
}

function delay(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function updateChatMemory(
  parsed: {
    chatId: string;
    sessionId: string;
    character: Character;
    messages: Message[];
    turnAction: ChatTurnAction;
  },
  user: AuthUser | null,
  assistantContent: string,
) {
  if (process.env.MEMORY_ENABLED === "0") {
    return;
  }

  const key = {
    sessionId: user?.id ?? parsed.sessionId,
    chatId: parsed.chatId,
    characterId: parsed.character.id,
  };
  const turn: MemoryTurn = {
    userContent: getTurnUserContent(parsed.messages, parsed.turnAction),
    assistantContent,
    messages: [
      ...parsed.messages,
      {
        id: `memory-${crypto.randomUUID()}`,
        role: "assistant",
        content: assistantContent,
        createdAt: new Date().toISOString(),
      },
    ],
  };

  await appendMemoryTurn({ ...key, turn });
  enqueueMemoryStateUpdate(key, parsed.character, turn);
}

function enqueueMemoryStateUpdate(
  key: MemoryUpdateKey,
  character: Character,
  turn: MemoryTurn,
) {
  const queueKey = getMemoryQueueKey(key);
  let item = memoryUpdateQueue.get(queueKey);
  if (!item) {
    item = {
      character,
      flushing: false,
      key,
      timer: null,
      turns: [],
    };
    memoryUpdateQueue.set(queueKey, item);
  }

  item.character = character;
  item.turns.push(turn);

  if (item.timer) {
    clearTimeout(item.timer);
  }

  const idleMs = getNonNegativeNumberEnv(
    "MEMORY_IDLE_UPDATE_MS",
    DEFAULT_MEMORY_IDLE_UPDATE_MS,
  );
  item.timer = setTimeout(() => {
    void flushMemoryStateUpdate(queueKey).catch(() => undefined);
  }, idleMs);
  unrefTimer(item.timer);
}

async function flushMemoryStateUpdate(queueKey: string) {
  const item = memoryUpdateQueue.get(queueKey);
  if (!item || item.flushing) {
    return;
  }

  if (item.timer) {
    clearTimeout(item.timer);
    item.timer = null;
  }

  const turns = item.turns.splice(0);
  if (!turns.length) {
    memoryUpdateQueue.delete(queueKey);
    return;
  }

  item.flushing = true;
  try {
    await applyQueuedMemoryStateUpdate(
      item.key,
      item.character,
      combineMemoryTurns(turns),
      turns.length,
    );
  } finally {
    item.flushing = false;
    if (item.turns.length) {
      const idleMs = getNonNegativeNumberEnv(
        "MEMORY_IDLE_UPDATE_MS",
        DEFAULT_MEMORY_IDLE_UPDATE_MS,
      );
      item.timer = setTimeout(() => {
        void flushMemoryStateUpdate(queueKey).catch(() => undefined);
      }, idleMs);
      unrefTimer(item.timer);
    } else {
      memoryUpdateQueue.delete(queueKey);
    }
  }
}

async function applyQueuedMemoryStateUpdate(
  key: MemoryUpdateKey,
  character: Character,
  turn: MemoryTurn,
  turnCountIncrement: number,
) {
  let update = null;

  if (process.env.MEMORY_LLM_ENABLED !== "0") {
    try {
      const runtimeConfig = await getProviderRuntime(
        character.modelId,
        process.env.MEMORY_MODEL
          ? {
              provider:
                process.env.AI_PROVIDER?.trim().toLowerCase() === "openai"
                  ? "openai"
                  : process.env.AI_PROVIDER?.trim().toLowerCase() === "lmstudio"
                    ? "lmstudio"
                    : "ollama",
              model: process.env.MEMORY_MODEL,
            }
          : undefined,
      );
      const currentState = await readMemoryState(key);
      const response = await fetchChatCompletion(runtimeConfig.baseUrl, {
        apiKey: runtimeConfig.apiKey,
        provider: runtimeConfig.provider,
        model: runtimeConfig.model,
        messages: buildMemoryUpdatePrompt({
          character,
          currentState,
          turn,
        }),
        maxTokens: 512,
        stream: false,
        temperature: 0.2,
        timeoutMs: getNumberEnv("MEMORY_UPDATE_TIMEOUT_MS", 20_000),
      });

      if (response.ok) {
        const payload = (await response.json()) as ChatCompletionResponse;
        const content = getCompletionContent(payload);
        update = parseMemoryUpdate(content);
      }
    } catch {
      update = null;
    }
  }

  await applyMemoryUpdate({ ...key, turn, turnCountIncrement, update });
}

function combineMemoryTurns(turns: MemoryTurn[]): MemoryTurn {
  if (turns.length === 1) {
    return turns[0];
  }

  const now = new Date().toISOString();
  return {
    userContent: turns
      .map((turn, index) => `Turn ${index + 1} user: ${turn.userContent}`)
      .join("\n"),
    assistantContent: turns
      .map(
        (turn, index) => `Turn ${index + 1} assistant: ${turn.assistantContent}`,
      )
      .join("\n"),
    messages: turns.flatMap((turn, index) => [
      {
        id: `memory-batch-${index}-user-${crypto.randomUUID()}`,
        role: "user" as const,
        content: turn.userContent,
        createdAt: now,
      },
      {
        id: `memory-batch-${index}-assistant-${crypto.randomUUID()}`,
        role: "assistant" as const,
        content: turn.assistantContent,
        createdAt: now,
      },
    ]),
  };
}

function getMemoryQueueKey(key: MemoryUpdateKey) {
  return [key.sessionId, key.chatId, key.characterId].join("\u0000");
}

function unrefTimer(timer: ReturnType<typeof setTimeout>) {
  if (
    timer &&
    typeof timer === "object" &&
    "unref" in timer &&
    typeof timer.unref === "function"
  ) {
    timer.unref();
  }
}

function getNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function getNonNegativeNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}
