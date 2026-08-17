import { NextResponse } from "next/server";
import {
  authenticateUser,
  createSessionCookie,
  createUserSession,
} from "@/lib/auth";
import { readAccountState } from "@/lib/account-data";
import { getRateLimitError } from "@/lib/rate-limit";

export const runtime = "nodejs";

type LoginBody = {
  name?: unknown;
  password?: unknown;
};

export async function POST(request: Request) {
  const rateLimitError = getRateLimitError(request, {
    keyPrefix: "auth-login",
    maxRequests: 8,
    windowMs: 5 * 60_000,
  });
  if (rateLimitError) {
    return rateLimitError;
  }

  try {
    const body = (await request.json()) as LoginBody;
    if (typeof body.name !== "string" || typeof body.password !== "string") {
      return NextResponse.json(
        { error: "이름과 비밀번호를 입력하세요." },
        { status: 400 },
      );
    }

    const user = await authenticateUser({
      name: body.name,
      password: body.password,
    });
    const token = await createUserSession(user.id, request);
    const state = await readAccountState(user.id);
    const response = NextResponse.json({ user, state });
    response.headers.append("Set-Cookie", createSessionCookie(token));
    return response;
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "로그인에 실패했습니다.",
      },
      { status: 401 },
    );
  }
}
