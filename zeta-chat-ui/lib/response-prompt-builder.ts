import {
  getCharacterResponsePromptSectionKey,
  readPromptSections,
  type ResponsePromptSectionKey,
} from "@/lib/prompt-store";
import type { Character, ResponseStyle } from "@/types/chat";

export async function getResponseFormatPrompt(
  character: Character,
  style: ResponseStyle,
) {
  const sections = await readPromptSections();
  const responseKey =
    `response.${style.flavor}.${style.length}` as ResponsePromptSectionKey;
  const characterResponseKey = getCharacterResponsePromptSectionKey(
    character.id,
    responseKey,
  );
  const personaPrefix =
    character.id === "areum" || character.id === "han-areum"
      ? "hanAreum"
      : "generic";
  const responsePrompt =
    sections[characterResponseKey]?.trim() || sections[responseKey]?.trim();

  if (responsePrompt) {
    return [responsePrompt, sections["shared.rules"]].join("\n\n");
  }

  return [
    sections[`${personaPrefix}.${style.flavor}`],
    sections[`length.${style.length}`],
    sections["shared.rules"],
  ].join("\n\n");
}
