import {
  getDataPath,
  readJsonFile,
  withFileLock,
  writeJsonFile,
} from "@/lib/server-files";
import type { ProviderSettings } from "@/types/chat";

const PROVIDER_SETTINGS_FILE_NAME = "provider-settings.json";

export function getProviderSettingsPath() {
  return getDataPath(PROVIDER_SETTINGS_FILE_NAME);
}

export function getDefaultProviderSettings(): ProviderSettings {
  return {
    deepseekApiKey: "",
  };
}

export async function readProviderSettings(): Promise<ProviderSettings> {
  return normalizeProviderSettings(
    await readJsonFile<unknown>(
      getProviderSettingsPath(),
      getDefaultProviderSettings(),
    ),
  );
}

export async function saveProviderSettings(
  input: unknown,
): Promise<ProviderSettings> {
  const settings = normalizeProviderSettings(input);
  const filePath = getProviderSettingsPath();
  await withFileLock(filePath, async () => {
    await writeJsonFile(filePath, settings);
  });

  return settings;
}

export async function getDeepSeekApiKey() {
  const settings = await readProviderSettings();
  return settings.deepseekApiKey;
}

function normalizeProviderSettings(input: unknown): ProviderSettings {
  if (!input || typeof input !== "object") {
    return getDefaultProviderSettings();
  }

  const record = input as Partial<ProviderSettings>;
  return {
    deepseekApiKey:
      typeof record.deepseekApiKey === "string"
        ? record.deepseekApiKey.trim()
        : "",
  };
}
