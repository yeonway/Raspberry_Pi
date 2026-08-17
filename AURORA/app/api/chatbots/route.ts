import { NextResponse } from "next/server";
import { readBotConfig } from "@/lib/bot-config";
import { readPromptCategoryConfig } from "@/lib/prompt-store";
import { createResponseOptionConfig } from "@/lib/response-formats";

export const runtime = "nodejs";

export async function GET() {
  const [botConfig, promptConfig] = await Promise.all([
    readBotConfig(),
    readPromptCategoryConfig(),
  ]);

  return NextResponse.json({
    ...botConfig,
    responseOptions: createResponseOptionConfig(promptConfig.categories),
  });
}
