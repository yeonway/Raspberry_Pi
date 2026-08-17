import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import {
  readFeatureFlags,
  saveFeatureFlags,
  readNotes,
  saveNotes,
  readNotifications,
  saveNotifications,
  appendAuditLog,
  checkSettingsCollisions,
  appendABTestResult,
  testLorebookActivation,
  readAuditLog,
  readABTestResults,
} from "@/lib/admin-store";
import type { AdminNote, FeatureFlags } from "@/lib/admin-store";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) return authError;

  const url = new URL(request.url);
  const category = url.searchParams.get("category");

  const [features, notes, auditLog, notifications, abTests] = await Promise.all([
    readFeatureFlags(),
    readNotes(),
    readAuditLog(500),
    readNotifications(),
    readABTestResults(200),
  ]);

  return NextResponse.json({
    features,
    notes,
    auditLog: category ? auditLog.filter((e) => e.category === category) : auditLog,
    notifications,
    abTests,
  });
}

export async function POST(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) return authError;

  const body = await request.json() as Record<string, unknown>;
  const action = body.action as string;

  try {
    switch (action) {
      case "saveFeatures": {
        const flags = body.flags as FeatureFlags;
        if (!flags || typeof flags !== "object") return NextResponse.json({ error: "flags required" }, { status: 400 });
        const saved = await saveFeatureFlags(flags);
        await appendAuditLog({ category: "operation", action: "features_updated", target: "feature_flags", adminUser: "admin" });
        return NextResponse.json({ features: saved });
      }

      case "saveNote": {
        const note = body.note as Record<string, unknown>;
        if (!note) return NextResponse.json({ error: "note required" }, { status: 400 });
        const notes = await readNotes();
        if (note.id) {
          const idx = notes.findIndex((x) => x.id === (note.id as string));
          const updated = { ...(idx >= 0 ? notes[idx] : {}), ...note, updatedAt: new Date().toISOString() } as unknown as AdminNote;
          if (idx >= 0) notes[idx] = updated;
          else notes.unshift(updated);
        } else {
          notes.unshift({
            id: crypto.randomUUID(), title: (note.title as string) ?? "", content: (note.content as string) ?? "",
            links: (note.links as string[]) ?? [], isArchived: false,
            createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
          } as AdminNote);
        }
        return NextResponse.json({ notes: await saveNotes(notes) });
      }

      case "deleteNote": {
        const notes = await readNotes();
        return NextResponse.json({ notes: await saveNotes(notes.filter((n) => n.id !== (body.noteId as string))) });
      }

      case "archiveNote": {
        const notes = await readNotes();
        const idx = notes.findIndex((n) => n.id === (body.noteId as string));
        if (idx >= 0) notes[idx].isArchived = !notes[idx].isArchived;
        return NextResponse.json({ notes: await saveNotes(notes) });
      }

      case "markNotifRead": {
        const notifs = await readNotifications();
        const idx = notifs.findIndex((n) => n.id === (body.notifId as string));
        if (idx >= 0) notifs[idx].read = true;
        return NextResponse.json({ notifications: await saveNotifications(notifs) });
      }

      case "markAllNotifsRead": {
        const notifs = await readNotifications();
        return NextResponse.json({ notifications: await saveNotifications(notifs.map((n) => ({ ...n, read: true }))) });
      }

      case "checkCollisions":
        return NextResponse.json({ collisions: await checkSettingsCollisions(body as Parameters<typeof checkSettingsCollisions>[0]) });

      case "saveABTest": {
        const entry = {
          prompt: body.prompt as string,
          model: (body.model as string) ?? "",
          configA: body.configA as { prompt?: string; model?: string; temperature?: number },
          configB: body.configB as { prompt?: string; model?: string; temperature?: number },
          responseA: (body.responseA as string) ?? "",
          responseB: (body.responseB as string) ?? "",
          winner: body.winner as "A" | "B" | "tie",
        };
        await appendABTestResult(entry);
        return NextResponse.json({ success: true });
      }

      case "testLorebooks": {
        const text = body.text as string;
        if (!text) return NextResponse.json({ error: "text required" }, { status: 400 });
        return NextResponse.json({ lorebookTest: await testLorebookActivation(text) });
      }

      default:
        return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
    }
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
