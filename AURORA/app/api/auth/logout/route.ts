import { NextResponse } from "next/server";
import {
  createExpiredSessionCookie,
  getSessionToken,
  revokeUserSession,
} from "@/lib/auth";

export const runtime = "nodejs";

export async function POST(request: Request) {
  await revokeUserSession(getSessionToken(request));
  const response = NextResponse.json({ ok: true });
  response.headers.append("Set-Cookie", createExpiredSessionCookie());
  return response;
}
