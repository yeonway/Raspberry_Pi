import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import { getBotConfigPath, readBotConfig, saveBotConfig } from "@/lib/bot-config";
import {
  getProviderSettingsPath,
  readProviderSettings,
  saveProviderSettings,
} from "@/lib/provider-settings";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  return NextResponse.json({
    ...(await readBotConfig()),
    providerSettings: await readProviderSettings(),
    providerSettingsPath: getProviderSettingsPath(),
    path: getBotConfigPath(),
  });
}

export async function POST(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  try {
    const body = await request.json();
    const providerSettingsInput =
      body && typeof body === "object" && "providerSettings" in body
        ? (body as { providerSettings?: unknown }).providerSettings
        : await readProviderSettings();
    const [saved, providerSettings] = await Promise.all([
      saveBotConfig(body),
      saveProviderSettings(providerSettingsInput),
    ]);
    return NextResponse.json({
      ...saved,
      providerSettings,
      providerSettingsPath: getProviderSettingsPath(),
      path: getBotConfigPath(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "챗봇 설정을 저장하지 못했습니다.",
      },
      { status: 400 },
    );
  }
}
