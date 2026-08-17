import type {
  ChatMemoryState,
  MemoryTurn,
  MemoryUpdate,
} from "@/lib/chat-memory";
import type { Character } from "@/types/chat";

export function buildMemoryUpdatePrompt(input: {
  character: Character;
  currentState: ChatMemoryState;
  turn: MemoryTurn;
}) {
  const shouldRefreshSummary =
    input.currentState.turnCount %
      getNumberEnv("MEMORY_SUMMARY_TURN_INTERVAL", 10) ===
    0;
  const recentMessages = input.turn.messages
    .slice(-16)
    .map((message) => `${message.role}: ${message.content}`)
    .join("\n");

  return [
    {
      role: "system" as const,
      content: [
        "You are a memory manager for a Korean Zeta-style character chat app.",
        "Return only valid JSON. Do not wrap it in markdown.",
        "The app stores full raw messages separately, so extract compact long-term memory only.",
        shouldRefreshSummary
          ? "Refresh the rolling summary so it preserves important old context and the latest turn."
          : "Keep summary stable unless the latest turn changes the long-term story.",
      ].join("\n"),
    },
    {
      role: "user" as const,
      content: JSON.stringify(
        {
          schema: {
            summary: "string",
            profile: {
              stable_user_fact_key: "short value",
            },
            preferences: {
              reply_preference_key: "short value",
            },
            relationship: {
              intimacy: 0.1,
              trust: 0.1,
              mood: "current relationship mood",
              dynamic: "how user and character currently relate",
              openLoops: ["promises, plans, unresolved topics"],
              boundaries: ["known user boundaries or dislikes"],
            },
            events: [
              {
                title: "short event title",
                description: "event-centered memory, not raw transcript",
                emotion: "optional emotion",
                importance: 0.1,
              },
            ],
            graph: [
              {
                subject: "user or named person",
                relation: "relationship or event relation",
                object: "target person, preference, object, event",
              },
            ],
            documents: [
              {
                kind: "turn | event | summary | profile | preference | relationship",
                text: "searchable memory text",
                importance: 0.1,
              },
            ],
          },
          character: {
            id: input.character.id,
            name: input.character.name,
            personaSummary: input.character.personaSummary,
          },
          previousState: {
            summary: input.currentState.summary,
            profile: input.currentState.profile,
            preferences: input.currentState.preferences,
            relationship: input.currentState.relationship,
            events: input.currentState.events.slice(-20),
            graph: input.currentState.graph.slice(-30),
            chunks: input.currentState.chunks.slice(-8),
          },
          recentMessages,
          latestTurn: {
            user: input.turn.userContent,
            assistant: input.turn.assistantContent,
          },
          rules: [
            "Preserve facts about user identity, preferences, relationships, devices, promises, and important emotional events.",
            "For Zeta-style memory, write events as shared story memories.",
            "Track relationship mood, open loops, and boundaries so the character can maintain continuity.",
            "Extract reply preferences that should affect future answers, but keep them concise.",
            "Do not invent details that are not supported.",
            "Keep values concise Korean when possible.",
          ],
        },
        null,
        2,
      ),
    },
  ];
}

export function parseMemoryUpdate(raw: string): MemoryUpdate | null {
  const trimmed = raw.trim();
  const jsonText = trimmed
    .replace(/^```(?:json)?/i, "")
    .replace(/```$/i, "")
    .trim();

  try {
    const parsed = JSON.parse(jsonText) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as MemoryUpdate) : null;
  } catch {
    return null;
  }
}

function getNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}
