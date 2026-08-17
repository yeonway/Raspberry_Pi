import { NextResponse } from "next/server";
import {
  fetchChatCompletion,
  getCompletionContent,
  getProviderRuntime,
} from "@/lib/chat-provider";
import type { OpenAIMessage } from "@/lib/chat-prompts";
import type { Character, Message } from "@/types/chat";

type SuggestRequest = {
  character: Character;
  messages: Message[];
  currentInput: string;
};

const SUGGEST_MAX_TOKENS = 128;

export const runtime = "nodejs";

export async function POST(request: Request) {
  let body: SuggestRequest;

  try {
    body = (await request.json()) as SuggestRequest;
    if (!body.character?.personaSummary) {
      return NextResponse.json(
        { error: "Character information is required." },
        { status: 400 },
      );
    }
  } catch {
    return NextResponse.json(
      { error: "Invalid request body." },
      { status: 400 },
    );
  }

  const { character, messages, currentInput } = body;

  try {
    const provider = await getProviderRuntime(character.modelId);
    const recentMessages = messages.slice(-8);

    const conversationLines = formatConversation(recentMessages);
    const systemPrompt = buildSuggestionPrompt(
      character,
      conversationLines,
      !!currentInput.trim(),
    );

    const promptMessages: OpenAIMessage[] = [
      { role: "system", content: systemPrompt },
      ...(currentInput.trim()
        ? [
            {
              role: "user" as const,
              content: `Complete this started message naturally in Korean, staying in character: "${currentInput.trim()}"`,
            },
          ]
        : [
            {
              role: "user" as const,
              content: "Write a natural next message the user would send in this conversation.",
            },
          ]),
    ];

    const response = await fetchChatCompletion(provider.baseUrl, {
      apiKey: provider.apiKey,
      provider: provider.provider,
      model: provider.model,
      messages: promptMessages,
      maxTokens: SUGGEST_MAX_TOKENS,
      stream: false,
      temperature: 0.9,
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      return NextResponse.json(
        { error: `Suggestion API error (${response.status}): ${detail.slice(0, 120)}` },
        { status: 502 },
      );
    }

    const payload = await response.json();
    const content = getCompletionContent(payload);
    const cleaned = cleanSuggestion(content, currentInput.trim());

    if (!cleaned) {
      return NextResponse.json(
        { error: "Could not generate a suggestion." },
        { status: 500 },
      );
    }

    return NextResponse.json({ content: cleaned });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Suggestion generation failed.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

function formatConversation(messages: Message[]) {
  if (messages.length === 0) {
    return "(No conversation yet)";
  }

  return messages
    .map((m) => `${m.role === "user" ? "사용자" : "캐릭터"}: ${m.content}`)
    .join("\n");
}

function buildSuggestionPrompt(
  character: Character,
  conversation: string,
  hasInput: boolean,
) {
  const persona = character.personaSummary
    .replace(/\$\$[\s\S]*?\$\$/g, "")
    .replace(/\$\$/g, "")
    .trim();

  return [
    "You are a writing assistant that suggests what a user could say next in a roleplay chat.",
    "",
    `Partner character: ${character.name}`,
    `Character description: ${character.intro}`,
    persona ? `Character persona: ${persona}` : "",
    "",
    "Recent conversation:",
    conversation,
    "",
    hasInput
      ? "The user has already started typing a message. Complete ONLY the started message naturally. Do NOT write a separate new message or add any commentary. Just output the completed Korean sentence."
      : "Suggest ONE short, natural Korean message (1-2 lines max) the user could send next. Do NOT output anything else — just the raw message text.",
    "The message must match the user's tone (casual Korean, 반말 or 존댓말 based on context).",
    "Do NOT roleplay as the character. Write what the USER should say.",
  ]
    .filter(Boolean)
    .join("\n");
}

function cleanSuggestion(raw: string, currentInput: string) {
  let cleaned = raw
    .replace(/^["'「『""]+/, "")
    .replace(/["'」』""]+$/, "")
    .replace(/^[:\-\s]+/, "")
    .trim();

  if (currentInput && cleaned.startsWith(currentInput)) {
    cleaned = cleaned.slice(currentInput.length).trimStart();
  }

  if (cleaned.length > 300) {
    cleaned = cleaned.slice(0, 300);
  }

  const firstNewline = cleaned.indexOf("\n");
  if (firstNewline > 0) {
    cleaned = cleaned.slice(0, firstNewline).trimEnd();
  }

  return cleaned;
}
