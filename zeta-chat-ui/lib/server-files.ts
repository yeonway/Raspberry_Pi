import { randomUUID } from "crypto";
import { mkdir, readFile, rename, writeFile } from "fs/promises";
import path from "path";

const DEFAULT_DATA_DIR = path.join(process.cwd(), "data");
const fileLocks = new Map<string, Promise<void>>();

export function getDataDir() {
  return process.env.CHAT_LOG_DIR ?? DEFAULT_DATA_DIR;
}

export function getDataPath(...segments: string[]) {
  return path.join(getDataDir(), ...segments);
}

export function sanitizePathSegment(value: string) {
  return (
    value
      .trim()
      .replace(/[^a-zA-Z0-9\uac00-\ud7a3_-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "default"
  );
}

export async function readJsonFile<T>(
  filePath: string,
  fallback: T,
  options: { recoverTrailingData?: boolean } = {},
): Promise<T> {
  try {
    const raw = await readFile(filePath, "utf8");
    const trimmed = raw.trim();
    if (!trimmed) {
      return fallback;
    }

    return (
      options.recoverTrailingData
        ? parseJsonWithRecoverableTrailingData(trimmed, fallback)
        : JSON.parse(trimmed)
    ) as T;
  } catch (error) {
    if (isNotFoundError(error)) {
      return fallback;
    }

    throw error;
  }
}

export async function writeJsonFile(filePath: string, value: unknown) {
  await writeFileAtomic(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

export async function writeTextFile(filePath: string, value: string) {
  await writeFileAtomic(filePath, value);
}

export async function withFileLock<T>(
  lockKey: string,
  operation: () => Promise<T>,
): Promise<T> {
  const previousLock =
    fileLocks.get(lockKey)?.catch(() => undefined) ?? Promise.resolve();
  let releaseLock: () => void = () => undefined;
  const currentLock = new Promise<void>((resolve) => {
    releaseLock = resolve;
  });
  const queuedLock = previousLock.then(() => currentLock);

  fileLocks.set(lockKey, queuedLock);

  await previousLock;
  try {
    return await operation();
  } finally {
    releaseLock();
    if (fileLocks.get(lockKey) === queuedLock) {
      fileLocks.delete(lockKey);
    }
  }
}

async function writeFileAtomic(filePath: string, value: string) {
  await mkdir(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.${randomUUID()}.tmp`;
  await writeFile(tempPath, value, "utf8");
  await rename(tempPath, filePath);
}

export function isNotFoundError(error: unknown) {
  return error instanceof Error && "code" in error && error.code === "ENOENT";
}

export function parseJsonWithRecoverableTrailingData(
  raw: string,
  fallback: unknown,
) {
  const trimmed = raw.trim();
  if (!trimmed) {
    return fallback;
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    const endIndex = findFirstJsonValueEnd(trimmed);
    if (endIndex > 0) {
      return JSON.parse(trimmed.slice(0, endIndex));
    }

    throw new Error("JSON file contains invalid data.");
  }
}

function findFirstJsonValueEnd(input: string) {
  const first = input[0];
  if (first !== "{" && first !== "[") {
    return -1;
  }

  const stack = [first];
  let inString = false;
  let escaped = false;

  for (let index = 1; index < input.length; index += 1) {
    const char = input[index];

    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === '"') {
        inString = false;
      }
      continue;
    }

    if (char === '"') {
      inString = true;
      continue;
    }

    if (char === "{" || char === "[") {
      stack.push(char);
      continue;
    }

    const expectedOpen = char === "}" ? "{" : char === "]" ? "[" : "";
    if (!expectedOpen) {
      continue;
    }

    if (stack.pop() !== expectedOpen) {
      return -1;
    }

    if (stack.length === 0) {
      return index + 1;
    }
  }

  return -1;
}
