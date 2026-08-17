import { NextResponse } from "next/server";
import {
  deleteAccountRoom,
  normalizeAccountRoom,
  writeAccountRoom,
} from "@/lib/account-data";
import { getCurrentUser } from "@/lib/auth";
import { getRateLimitError } from "@/lib/rate-limit";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const rateLimitError = getAccountWriteRateLimitError(request);
  if (rateLimitError) {
    return rateLimitError;
  }

  const user = await getCurrentUser(request);
  if (!user) {
    return NextResponse.json(
      { error: "Login is required to save chats." },
      { status: 401 },
    );
  }

  const body = (await request.json().catch(() => null)) as {
    room?: unknown;
  } | null;
  const room = normalizeAccountRoom(body?.room);

  if (!room) {
    return NextResponse.json({ error: "room is invalid." }, { status: 400 });
  }

  await writeAccountRoom(user.id, room);
  return NextResponse.json({ room });
}

export async function DELETE(request: Request) {
  const rateLimitError = getAccountWriteRateLimitError(request);
  if (rateLimitError) {
    return rateLimitError;
  }

  const user = await getCurrentUser(request);
  if (!user) {
    return NextResponse.json(
      { error: "Login is required to delete chats." },
      { status: 401 },
    );
  }

  const { searchParams } = new URL(request.url);
  const roomId = searchParams.get("roomId")?.trim();
  if (!roomId) {
    return NextResponse.json({ error: "roomId is required." }, { status: 400 });
  }

  await deleteAccountRoom(user.id, roomId);
  return NextResponse.json({ ok: true });
}

function getAccountWriteRateLimitError(request: Request) {
  return getRateLimitError(request, {
    keyPrefix: "account-write",
    maxRequests: 120,
    windowMs: 60_000,
  });
}
