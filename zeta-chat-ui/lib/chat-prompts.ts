import { getResponseFormatPrompt } from "@/lib/response-prompt-builder";
import { getResponseLengthContract } from "@/lib/chat-response";
import type {
  AuthUser,
  Character,
  ChatTurnAction,
  Message,
  ResponseStyle,
} from "@/types/chat";

export type OpenAIMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

const DEFAULT_MODEL_CONTEXT_MESSAGES = 12;

export async function buildLmStudioMessages(
  character: Character,
  user: AuthUser | null,
  customCharacterPrompt: string,
  messages: Message[],
  responseStyle: ResponseStyle,
  memoryContext: string,
  turnAction: ChatTurnAction,
): Promise<OpenAIMessage[]> {
  const responseFormatPrompt = await getResponseFormatPrompt(
    character,
    responseStyle,
  );
  const responseLengthContract = getResponseLengthContract(responseStyle);
  const personaPrompt = buildPersonaPrompt(
    character.personaSummary,
    customCharacterPrompt,
  );
  const sceneMarkupContract =
    "When describing actions, atmosphere, body language, or scene context, wrap that narration in paired asterisks like *문을 조심스럽게 닫고 시선을 돌린다.* Keep spoken dialogue outside the asterisks.";

  const lmStudioMessages: OpenAIMessage[] = [
    {
      role: "system",
      content: [
        `You are ${character.name}, an AI chatbot in Zeta Chat.`,
        `Character description: ${character.intro}`,
        `First message: ${character.firstScene}`,
        personaPrompt
          ? `Persona and speech style: ${personaPrompt}`
          : "",
        user
          ? [
              `The user's account name is ${user.name}.`,
              `When replying directly to the user, address them as "${user.name}" instead of generic labels such as "user" or "사용자".`,
              `Use the name naturally in Korean sentences; do not repeat it in every sentence when it would sound awkward.`,
            ].join(" ")
          : "",
        memoryContext,
        responseFormatPrompt,
        "Stay in character, answer naturally in Korean, and do not mention system instructions.",
      ]
        .filter(Boolean)
        .join("\n\n"),
    },
    ...getModelContextMessages(messages).map((message) => ({
      role: message.role,
      content: message.content,
    })),
    {
      role: "system",
      content: [responseLengthContract, sceneMarkupContract]
        .filter(Boolean)
        .join("\n"),
    },
  ];

  if (turnAction === "skip") {
    lmStudioMessages.push({
      role: "user",
      content:
        "[Turn skipped] The user chose not to speak this turn. Continue the scene naturally as the character. You may describe the next situation, advance the moment, or have the character speak again. Do not mention that a skip button was pressed.",
    });
  }

  return lmStudioMessages;
}

function buildPersonaPrompt(
  basePersonaPrompt: string,
  customCharacterPrompt: string,
) {
  const basePrompt = basePersonaPrompt.trim();
  const customPrompt = customCharacterPrompt.trim();
  const slotPattern = /\$\$[\s\S]*?\$\$/;

  if (!basePrompt) {
    return customPrompt;
  }

  if (slotPattern.test(basePrompt)) {
    const promptWithSlot = customPrompt
      ? basePrompt.replace(slotPattern, customPrompt)
      : basePrompt;
    return promptWithSlot
      .split("$$")
      .join("")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  if (!customPrompt) {
    return basePrompt.split("$$").join("").trim();
  }

  return [
    basePrompt.split("$$").join("").trim(),
    "[USER CUSTOM CHARACTER SETTINGS - PRIORITY]",
    customPrompt,
  ].join("\n\n");
}

function getModelContextMessages(messages: Message[]) {
  const maxMessages = getNonNegativeNumberEnv(
    "CHAT_MODEL_MAX_MESSAGES",
    DEFAULT_MODEL_CONTEXT_MESSAGES,
  );

  if (maxMessages === 0 || messages.length <= maxMessages) {
    return messages;
  }

  return messages.slice(-maxMessages);
}

function getNonNegativeNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}
