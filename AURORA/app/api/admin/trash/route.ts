export const runtime = "nodejs";

import { NextRequest, NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import {
  readTrash,
  addToTrash,
  restoreFromTrash,
  permanentlyDeleteFromTrash,
  emptyTrash,
} from "@/lib/admin-store";

export async function GET(request: NextRequest) {
  const authError = await getAdminAuthError(request);
  if (authError) return authError;

  const trash = await readTrash();
  return NextResponse.json({ trash });
}

export async function POST(request: NextRequest) {
  const authError = await getAdminAuthError(request);
  if (authError) return authError;

  const body = await request.json();

  switch (body.action) {
    case "add": {
      await addToTrash(body.data);
      const trash = await readTrash();
      return NextResponse.json({ trash });
    }

    case "restore": {
      await restoreFromTrash(body.id);
      const trash = await readTrash();
      return NextResponse.json({ trash });
    }

    case "permanentDelete": {
      await permanentlyDeleteFromTrash(body.id);
      const trash = await readTrash();
      return NextResponse.json({ trash });
    }

    case "empty": {
      await emptyTrash();
      return NextResponse.json({ trash: [] });
    }

    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}
