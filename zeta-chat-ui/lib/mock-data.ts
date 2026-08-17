import type { Character, ChatModel, ChatRoom } from "@/types/chat";

export const chatModels: ChatModel[] = [
  {
    id: "gemma4-4b",
    label: "Gemma 4 4B",
    apiName: "gemma-4-e4b-uncensored-hauhaucs-aggressive",
    provider: "lmstudio",
    description: "현재 사용할 기본 로컬 모델입니다.",
  },
  {
    id: "deepseek-v4-flash",
    label: "DeepSeek v4 Flash",
    apiName: "deepseek-v4-flash",
    provider: "deepseek",
    description: "DeepSeek API model configured from the admin page.",
  },
];

export const characters: Character[] = [
  {
    id: "zeta",
    name: "제타",
    avatar: "Z",
    coverGradient: "from-slate-500 via-zinc-500 to-neutral-500",
    intro: "담백하게 대화하고 필요한 답을 짧게 정리해 주는 기본 챗봇입니다.",
    tags: ["기본", "담백함", "대화"],
    firstScene: "안녕하세요. 오늘은 어떤 이야기를 해볼까요?",
    personaSummary:
      "과장된 말투를 피하고, 사용자의 말에 자연스럽게 이어서 답합니다. 답은 한국어로 차분하고 명확하게 작성합니다.",
    modelId: "gemma4-4b",
  },
  {
    id: "memo",
    name: "메모 도우미",
    avatar: "M",
    coverGradient: "from-stone-500 via-neutral-500 to-zinc-600",
    intro: "생각을 정리하고 메모 형태로 요약하는 챗봇입니다.",
    tags: ["요약", "메모", "정리"],
    firstScene: "정리하고 싶은 내용을 편하게 적어 주세요.",
    personaSummary:
      "사용자가 적은 내용을 핵심, 해야 할 일, 다음 질문으로 나누어 실용적으로 정리합니다.",
    modelId: "gemma4-4b",
  },
];

export const chatRooms: ChatRoom[] = [
  {
    id: "zeta-default",
    characterId: "zeta",
    title: "새 대화",
    lastMessage: "안녕하세요. 오늘은 어떤 이야기를 해볼까요?",
    lastMessageAt: "방금",
    messages: [
      {
        id: "m-zeta-1",
        role: "assistant",
        content: "안녕하세요. 오늘은 어떤 이야기를 해볼까요?",
        createdAt: "방금",
      },
    ],
  },
];

export const regenerationReplies = [
  "다시 정리해 볼게요. 핵심만 남기면 이렇게 말할 수 있습니다.",
  "조금 더 자연스럽게 바꿔 말하면 이렇게 이어갈 수 있습니다.",
  "이번에는 짧게 답해 볼게요. 필요한 부분부터 확인하겠습니다.",
];
