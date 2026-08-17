export type MessageRole = "user" | "assistant";

export type Message = {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  isStreaming?: boolean;
};

export type Character = {
  id: string;
  name: string;
  avatar: string;
  avatarImageUrl?: string;
  coverGradient: string;
  intro: string;
  tags: string[];
  firstScene: string;
  personaSummary: string;
  modelId: string;
};

export type ChatRoom = {
  id: string;
  characterId: string;
  title: string;
  lastMessage: string;
  lastMessageAt: string;
  archivedAt?: string;
  customCharacterPrompt?: string;
  messages: Message[];
};

export type ResponseFlavor = "safe" | "intense";

export type ResponseLength = "short" | "medium" | "long";

export type ResponseStyle = {
  flavor: ResponseFlavor;
  length: ResponseLength;
};

export type ResponseFlavorOption = {
  value: ResponseFlavor;
  label: string;
  description: string;
};

export type ResponseLengthOption = {
  value: ResponseLength;
  label: string;
  description: string;
};

export type ResponseOptionConfig = {
  flavors: ResponseFlavorOption[];
  lengths: ResponseLengthOption[];
};

export type ChatTurnAction = "message" | "skip";

export type AuthUser = {
  id: string;
  name: string;
};

export type MemoryItem = {
  id: string;
  chatId: string;
  chatTitle: string;
  characterId: string;
  characterName: string;
  summary: string;
  recentCreatedAt: string;
  createdAt: string;
};

export type AccountChatState = {
  rooms: ChatRoom[];
  memories: MemoryItem[];
  responseStyle?: ResponseStyle;
};

export type ChatModel = {
  id: string;
  label: string;
  apiName: string;
  provider: ChatProvider;
  description: string;
};

export type ChatProvider = "lmstudio" | "ollama" | "openai" | "deepseek";

export type ModelSelection = {
  provider: ChatProvider;
  model: string;
};

export type RuntimeModel = {
  id: string;
  label: string;
  apiName: string;
  provider: ChatProvider;
  description?: string;
  source: "lmstudio" | "ollama" | "configured" | "fallback";
};

export type ProviderStatus = {
  id: ChatProvider;
  label: string;
  available: boolean;
  error?: string;
};

export type ChatModelsResult = {
  models: RuntimeModel[];
  defaultModel: ModelSelection;
  providers: ProviderStatus[];
  error?: string;
  updatedAt: string;
};

export type BotConfig = {
  models: ChatModel[];
  characters: Character[];
  defaultCharacterId: string;
};

export type ProviderSettings = {
  deepseekApiKey: string;
};

export type SendMessageInput = {
  chatId: string;
  sessionId: string;
  chatTitle?: string;
  character: Character;
  customCharacterPrompt?: string;
  messages: Message[];
  content: string;
  responseStyle: ResponseStyle;
  modelSelection?: ModelSelection;
  turnAction?: ChatTurnAction;
  stream?: boolean;
  signal?: AbortSignal;
  onToken?: (token: string) => void;
};

export type SendMessageResult = {
  content: string;
  memoryItem?: MemoryItem;
};

export type ChatLogEntry = {
  id: string;
  userId?: string;
  userName?: string;
  sessionKey?: string;
  sessionName?: string;
  clientSessionId?: string;
  sessionId: string;
  chatId: string;
  chatTitle?: string;
  characterId: string;
  characterName: string;
  responseStyle: ResponseStyle;
  requestedModel?: ModelSelection;
  usedModel?: ModelSelection;
  fallbackModel?: ModelSelection;
  usedFallbackModel?: boolean;
  turnAction?: ChatTurnAction;
  messages: Message[];
  assistantContent?: string;
  error?: string;
  createdAt: string;
};

export type ChatLogSession = {
  id: string;
  name: string;
  userId?: string;
  sessionIds: string[];
  chatIds: string[];
  chatTitles: string[];
  characterNames: string[];
  turnCount: number;
  errorCount: number;
  firstAt: string;
  lastAt: string;
  latestUserMessage?: string;
  latestAssistantContent?: string;
};

export type PromptCategory = {
  id: string;
  name: string;
  parentId?: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
};

export type PromptCategoryAssignment = {
  promptKey: string;
  categoryIds: string[];
};
