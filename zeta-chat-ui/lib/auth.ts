import { rm } from "fs/promises";
import {
  createHash,
  randomBytes,
  randomUUID,
  scrypt,
  timingSafeEqual,
} from "crypto";
import { promisify } from "util";
import {
  getDataPath,
  readJsonFile,
  withFileLock,
  writeJsonFile,
} from "@/lib/server-files";
import type { AuthUser } from "@/types/chat";

type StoredUser = AuthUser & {
  passwordHash: string;
  createdAt: string;
  updatedAt: string;
};

type StoredSession = {
  tokenHash: string;
  userId: string;
  createdAt: string;
  expiresAt: string;
};

const USERS_FILE_NAME = "auth-users.json";
const SESSIONS_FILE_NAME = "auth-sessions.json";
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;
export const SESSION_COOKIE_NAME = "zeta_session";

const scryptAsync = promisify(scrypt);

function getUsersPath() {
  return getDataPath(USERS_FILE_NAME);
}

function getSessionsPath() {
  return getDataPath(SESSIONS_FILE_NAME);
}

function normalizeName(name: string) {
  return name.trim().replace(/\s+/g, " ");
}

function getNameKey(name: string) {
  return normalizeName(name).toLocaleLowerCase("ko-KR");
}

function publicUser(user: StoredUser): AuthUser {
  return {
    id: user.id,
    name: user.name,
  };
}

function hashSessionToken(token: string) {
  return createHash("sha256").update(token).digest("hex");
}

async function readUsers() {
  return readJsonFile<StoredUser[]>(getUsersPath(), []);
}

async function writeUsers(users: StoredUser[]) {
  await writeJsonFile(getUsersPath(), users);
}

async function readSessions() {
  return readJsonFile<StoredSession[]>(getSessionsPath(), []);
}

async function writeSessions(sessions: StoredSession[]) {
  await writeJsonFile(getSessionsPath(), sessions);
}

async function hashPassword(password: string) {
  const salt = randomBytes(16).toString("hex");
  const derived = (await scryptAsync(password, salt, 64)) as Buffer;
  return `${salt}:${derived.toString("hex")}`;
}

async function verifyPassword(password: string, storedHash: string) {
  const [salt, hash] = storedHash.split(":");
  if (!salt || !hash) {
    return false;
  }

  const derived = (await scryptAsync(password, salt, 64)) as Buffer;
  const expected = Buffer.from(hash, "hex");
  return (
    expected.length === derived.length && timingSafeEqual(expected, derived)
  );
}

function validateNameInput(nameInput: string) {
  const name = normalizeName(nameInput);
  if (!name) {
    throw new Error("이름을 입력하세요.");
  }

  return name;
}

function validateCredentials(input: { name: string; password: string }) {
  const name = validateNameInput(input.name);
  if (!name) {
    throw new Error("이름을 입력하세요.");
  }

  if (input.password.length < 8) {
    throw new Error("비밀번호는 8자 이상이어야 합니다.");
  }

  return { name };
}

export async function registerUser(input: { name: string; password: string }) {
  const { name } = validateCredentials(input);
  return withFileLock(getUsersPath(), async () => {
    const users = await readUsers();
    const nameKey = getNameKey(name);

    if (users.some((user) => getNameKey(user.name) === nameKey)) {
      throw new Error("이미 사용 중인 이름입니다.");
    }

    const now = new Date().toISOString();
    const user: StoredUser = {
      id: randomUUID(),
      name,
      passwordHash: await hashPassword(input.password),
      createdAt: now,
      updatedAt: now,
    };

    await writeUsers([...users, user]);
    return publicUser(user);
  });
}

export async function authenticateUser(input: {
  name: string;
  password: string;
}) {
  const { name } = validateCredentials(input);
  const users = await readUsers();
  const nameKey = getNameKey(name);
  const user = users.find((item) => getNameKey(item.name) === nameKey);

  if (!user || !(await verifyPassword(input.password, user.passwordHash))) {
    throw new Error("이름 또는 비밀번호가 올바르지 않습니다.");
  }

  return publicUser(user);
}

export async function updateUserProfile(input: {
  userId: string;
  name: string;
}) {
  const name = validateNameInput(input.name);
  return withFileLock(getUsersPath(), async () => {
    const users = await readUsers();
    const userIndex = users.findIndex((user) => user.id === input.userId);

    if (userIndex < 0) {
      throw new Error("계정을 찾을 수 없습니다.");
    }

    const nameKey = getNameKey(name);
    const duplicateName = users.some(
      (user) => user.id !== input.userId && getNameKey(user.name) === nameKey,
    );

    if (duplicateName) {
      throw new Error("이미 사용 중인 이름입니다.");
    }

    const nextUser: StoredUser = {
      ...users[userIndex],
      name,
      updatedAt: new Date().toISOString(),
    };

    await writeUsers(
      users.map((user, index) => (index === userIndex ? nextUser : user)),
    );
    return publicUser(nextUser);
  });
}

export async function createUserSession(userId: string) {
  const token = randomBytes(32).toString("base64url");
  const now = new Date();
  const expiresAt = new Date(
    now.getTime() + SESSION_MAX_AGE_SECONDS * 1000,
  ).toISOString();
  await withFileLock(getSessionsPath(), async () => {
    const sessions = await readSessions();
    const activeSessions = sessions.filter(
      (session) => Date.parse(session.expiresAt) > Date.now(),
    );

    await writeSessions([
      ...activeSessions,
      {
        tokenHash: hashSessionToken(token),
        userId,
        createdAt: now.toISOString(),
        expiresAt,
      },
    ]);
  });

  return token;
}

export async function revokeUserSession(token: string | null) {
  if (!token) {
    return;
  }

  const tokenHash = hashSessionToken(token);
  await withFileLock(getSessionsPath(), async () => {
    const sessions = await readSessions();
    await writeSessions(
      sessions.filter((session) => session.tokenHash !== tokenHash),
    );
  });
}

export async function getUserBySessionToken(token: string | null) {
  if (!token) {
    return null;
  }

  const tokenHash = hashSessionToken(token);
  const [users, sessions] = await Promise.all([readUsers(), readSessions()]);
  const session = sessions.find(
    (item) =>
      item.tokenHash === tokenHash && Date.parse(item.expiresAt) > Date.now(),
  );
  if (!session) {
    return null;
  }

  const user = users.find((item) => item.id === session.userId);
  return user ? publicUser(user) : null;
}

export function getSessionToken(request: Request) {
  const cookie = request.headers.get("cookie") ?? "";
  const parts = cookie.split(";").map((part) => part.trim());
  const match = parts.find((part) =>
    part.startsWith(`${SESSION_COOKIE_NAME}=`),
  );
  return match
    ? decodeURIComponent(match.slice(SESSION_COOKIE_NAME.length + 1))
    : null;
}

export async function getCurrentUser(request: Request) {
  return getUserBySessionToken(getSessionToken(request));
}

export function createSessionCookie(token: string) {
  return `${SESSION_COOKIE_NAME}=${encodeURIComponent(
    token,
  )}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${SESSION_MAX_AGE_SECONDS}`;
}

export function createExpiredSessionCookie() {
  return `${SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`;
}

export async function deleteAccountDataFiles(userId: string) {
  await rm(getDataPath("accounts", userId), {
    recursive: true,
    force: true,
  });
}
