export type ChatV2FeedItem =
  | ChatV2TextMessage
  | ChatV2GeneratedImage
  | ChatV2SceneInfo
  | ChatV2SystemNotice
  | ChatV2TypingIndicator;

export type ChatV2TextMessage = {
  type: "message";
  id: string;
  sender: "ai" | "user";
  characterId?: string;
  content: string;
  providerLabel?: string;
  createdAt: string;
};

export type ChatV2GeneratedImage = {
  type: "image";
  id: string;
  imageUrl: string;
  alt?: string;
  aspectRatio?: number;
  generationStatus?: "generating" | "done" | "failed";
  relatedMessageId?: string;
  createdAt: string;
};

export type ChatV2SceneInfo = {
  type: "sceneInfo";
  id: string;
  date?: string;
  time?: string;
  location?: string;
  collapsed?: boolean;
  createdAt: string;
};

export type ChatV2SystemNotice = {
  type: "system";
  id: string;
  content: string;
  createdAt: string;
};

export type ChatV2TypingIndicator = {
  type: "typing";
  id: string;
  characterId: string;
};

export type ChatV2Character = {
  id: string;
  name: string;
  avatarUrl?: string;
  avatarColor?: string;
  nameColor?: string;
  role?: string;
};

export type ChatV2Room = {
  id: string;
  title: string;
  modelName: string;
  characters: ChatV2Character[];
  feedItems: ChatV2FeedItem[];
};
