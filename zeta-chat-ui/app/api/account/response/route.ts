import { NextResponse } from "next/server";
import {
  readAccountResponseStyle,
  writeAccountResponseStyle,
} from "@/lib/account-data";
import { getCurrentUser } from "@/lib/auth";
import { getRateLimitError } from "@/lib/rate-limit";
import { normalizeResponseStyle } from "@/lib/response-formats";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const user = await getCurrentUser(request);
  if (!user) {
    return NextResponse.json(
      { error: "Login is required to load response settings." },
      { status: 401 },
    );
  }

  const responseStyle = await readAccountResponseStyle(user.id);
  return NextResponse.json({ responseStyle });
}

export async function POST(request: Request) {
  const rateLimitError = getRateLimitError(request, {
    keyPrefix: "account-write",
    maxRequests: 120,
    windowMs: 60_000,
  });
  if (rateLimitError) {
    return rateLimitError;
  }

  const user = await getCurrentUser(request);
  if (!user) {
    return NextResponse.json(
      { error: "Login is required to save response settings." },
      { status: 401 },
    );
  }

  const body = (await request.json().catch(() => null)) as {
    responseStyle?: unknown;
  } | null;
  if (!body || !body.responseStyle) {
    return NextResponse.json(
      { error: "responseStyle is required." },
      { status: 400 },
    );
  }

  const responseStyle = await writeAccountResponseStyle(
    user.id,
    normalizeResponseStyle(body.responseStyle),
  );
  return NextResponse.json({ responseStyle });
}
