import { NextResponse } from "next/server";
import { readAccountState } from "@/lib/account-data";
import { getCurrentUser } from "@/lib/auth";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const user = await getCurrentUser(request);
  if (!user) {
    return NextResponse.json({
      user: null,
      state: {
        rooms: [],
        memories: [],
      },
    });
  }

  const state = await readAccountState(user.id);
  return NextResponse.json({ user, state });
}
