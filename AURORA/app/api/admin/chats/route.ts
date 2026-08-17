import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import { readChatLogs, summarizeChatLogSessions } from "@/lib/chat-logs";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  const { searchParams } = new URL(request.url);
  const limit = Number(searchParams.get("limit") ?? 200);
  const logs = await readChatLogs(Number.isFinite(limit) ? limit : 200);
  const sessions = summarizeChatLogSessions(logs);

  return NextResponse.json({ logs, sessions });
}
