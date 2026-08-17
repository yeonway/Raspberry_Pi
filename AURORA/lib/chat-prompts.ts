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
  const sceneMarkupContract = [
    "# 출력 마크업 규칙 (반드시 준수)",
    "- 서술(행동·표정·분위기)은 ** 으로 양쪽을 감싼다.",
    "  예: **그녀는 조용히 고개를 끄덕이며 미소 지었다.**",
    "- 대사(말풍선)는 \"\" 으로 양쪽을 감싼다.",
    "  예: \"안녕? 오랜만이야.\"",
    "- **와 \"\"는 반드시 쌍으로 닫을 것.",
  ].join("\n");

  const roleplayRules = [
    "역할극 모드. 서술(**으로 감싼 부분)과 대사(\"\"으로 감싼 부분)로만 구성된 답변을 출력한다.",
    "반복·되풀이 금지. 사용자 행동/대사/감정을 대신 쓰지 말 것.",
    "캐릭터 말투·호칭·성격 일관 유지. 모르는 정보는 아는 척 말 것.",
    "이모지 금지. 해설·분석 없이 본문만 출력.",
  ].join("\n");

  const characterContext = [
    `[캐릭터: ${character.name}]`,
    `소개: ${character.intro}`,
    `첫메시지: ${character.firstScene}`,
  ].join("\n");

  const userContext = user
    ? `상대: ${user.name}`
    : "";

  const lmStudioMessages: OpenAIMessage[] = [
    {
      role: "system",
      content: [
        roleplayRules,
        characterContext,
        personaPrompt ? `페르소나 및 말투 지침:\n${personaPrompt}` : "",
        userContext,
        memoryContext,
        responseFormatPrompt,
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
