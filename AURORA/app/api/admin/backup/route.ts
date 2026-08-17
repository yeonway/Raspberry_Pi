import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import {
  readBackups,
  saveBackups,
  type BackupEntry,
} from "@/lib/admin-store";
import { getDataPath, isNotFoundError, withFileLock } from "@/lib/server-files";
import { mkdir, readFile, readdir, unlink, writeFile } from "fs/promises";
import path from "path";

export const runtime = "nodejs";

async function readDataFilesRecursive(
  dir: string,
  baseDir: string,
  skipNames: Set<string>,
): Promise<Array<{ path: string; content: string }>> {
  const files: Array<{ path: string; content: string }> = [];
  const entries = await readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    if (skipNames.has(entry.name)) {
      continue;
    }

    const fullPath = path.join(dir, entry.name);
    const relativePath = path.relative(baseDir, fullPath);

    if (entry.isDirectory()) {
      files.push(
        ...(await readDataFilesRecursive(fullPath, baseDir, skipNames)),
      );
    } else if (
      entry.isFile() &&
      !entry.name.endsWith(".tmp") &&
      !entry.name.endsWith(".tmp-download")
    ) {
      try {
        const content = await readFile(fullPath, "utf8");
        files.push({ path: relativePath, content });
      } catch {
        try {
          const content = await readFile(fullPath);
          files.push({ path: relativePath, content: content.toString("base64") });
        } catch {
          // skip unreadable files
        }
      }
    }
  }

  return files;
}

export async function GET(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  const { searchParams } = new URL(request.url);
  const downloadId = searchParams.get("download");

  if (downloadId) {
    const backups = await readBackups();
    const entry = backups.find((b) => b.id === downloadId);
    if (!entry) {
      return NextResponse.json(
        { error: "백업을 찾을 수 없습니다." },
        { status: 404 },
      );
    }

    const backupPath = getDataPath("backups", entry.filename);
    try {
      const content = await readFile(backupPath);
      return new NextResponse(content, {
        headers: {
          "Content-Type": "application/json",
          "Content-Disposition": `attachment; filename="${encodeURIComponent(entry.filename)}"`,
        },
      });
    } catch (error) {
      if (isNotFoundError(error)) {
        return NextResponse.json(
          { error: "백업 파일을 찾을 수 없습니다." },
          { status: 404 },
        );
      }
      throw error;
    }
  }

  const backups = await readBackups();
  return NextResponse.json({ backups });
}

export async function POST(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  const { searchParams } = new URL(request.url);
  const action = searchParams.get("action");

  try {
    switch (action) {
      case "create": {
        const dataDir = getDataPath();
        const backupDir = path.basename(getDataPath("backups"));
        const skipNames = new Set([backupDir]);
        const files = await readDataFilesRecursive(dataDir, dataDir, skipNames);
        const createdAt = new Date().toISOString();
        const timestamp = Date.now();
        const filename = `backup-${timestamp}.json`;
        const backupPath = getDataPath("backups", filename);

        const backupData = { files, createdAt };
        await mkdir(getDataPath("backups"), { recursive: true });
        await writeFile(backupPath, JSON.stringify(backupData, null, 2), "utf8");

        const stat = { size: Buffer.byteLength(JSON.stringify(backupData)) };
        const itemCounts: Record<string, number> = {};
        for (const f of files) {
          const dir = f.path.split(path.sep)[0] ?? "other";
          itemCounts[dir] = (itemCounts[dir] ?? 0) + 1;
        }

        const entry: BackupEntry = {
          id: crypto.randomUUID(),
          filename,
          version: "1.0",
          size: stat.size,
          itemCounts,
          createdAt,
        };

        const backups = await readBackups();
        backups.unshift(entry);
        await saveBackups(backups);

        return NextResponse.json({ entry, backups });
      }

      case "restore": {
        const body = (await request.json()) as { id?: string };
        if (!body.id) {
          return NextResponse.json(
            { error: "복원할 백업 ID가 필요합니다." },
            { status: 400 },
          );
        }

        const backups = await readBackups();
        const entry = backups.find((b) => b.id === body.id);
        if (!entry) {
          return NextResponse.json(
            { error: "백업을 찾을 수 없습니다." },
            { status: 404 },
          );
        }

        const backupPath = getDataPath("backups", entry.filename);
        const raw = await readFile(backupPath, "utf8");
        const backup = JSON.parse(raw) as {
          files?: Array<{ path: string; content: string }>;
        };

        if (!backup.files || !Array.isArray(backup.files)) {
          return NextResponse.json(
            { error: "백업 데이터가 유효하지 않습니다." },
            { status: 400 },
          );
        }

        const baseDir = getDataPath();
        for (const file of backup.files) {
          const targetPath = path.join(baseDir, file.path);
          await mkdir(path.dirname(targetPath), { recursive: true });

          let content: string | Buffer = file.content;
          if (content && typeof content === "string") {
            const isBinaryFile =
              /\.(png|jpg|jpeg|gif|webp|svg|mp3|wav|ogg|mp4|webm|pdf|zip|gz)$/i.test(
                file.path,
              );
            if (isBinaryFile) {
              try {
                content = Buffer.from(file.content, "base64");
                await writeFile(targetPath, content);
                continue;
              } catch {
                // fall through to write as utf8
              }
            }
          }

          await withFileLock(targetPath, () =>
            writeFile(targetPath, String(content ?? ""), "utf8"),
          );
        }

        return NextResponse.json({ success: true, restored: entry });
      }

      case "upload": {
        const body = (await request.json()) as { data?: unknown };
        if (!body.data) {
          return NextResponse.json(
            { error: "업로드할 백업 데이터가 필요합니다." },
            { status: 400 },
          );
        }

        let parsed: { files?: Array<{ path: string; content: string }> };
        try {
          parsed =
            typeof body.data === "string" ? JSON.parse(body.data) : body.data;
        } catch {
          return NextResponse.json(
            { error: "백업 데이터가 유효한 JSON이 아닙니다." },
            { status: 400 },
          );
        }

        if (!parsed.files || !Array.isArray(parsed.files)) {
          return NextResponse.json(
            { error: "백업 데이터에 files 배열이 필요합니다." },
            { status: 400 },
          );
        }

        const timestamp = Date.now();
        const filename = `backup-${timestamp}.json`;
        const backupPath = getDataPath("backups", filename);
        const createdAt = new Date().toISOString();

        const backupData = { files: parsed.files, createdAt };
        await mkdir(getDataPath("backups"), { recursive: true });
        await writeFile(
          backupPath,
          JSON.stringify(backupData, null, 2),
          "utf8",
        );

        const stat = { size: Buffer.byteLength(JSON.stringify(backupData)) };
        const itemCounts: Record<string, number> = {};
        for (const f of parsed.files) {
          const dir = f.path.split(path.sep)[0] ?? "other";
          itemCounts[dir] = (itemCounts[dir] ?? 0) + 1;
        }

        const entry: BackupEntry = {
          id: crypto.randomUUID(),
          filename,
          version: "1.0",
          size: stat.size,
          itemCounts,
          createdAt,
        };

        const backups = await readBackups();
        backups.unshift(entry);
        await saveBackups(backups);

        return NextResponse.json({ entry, backups });
      }

      case "delete": {
        const body = (await request.json()) as { id?: string };
        if (!body.id) {
          return NextResponse.json(
            { error: "삭제할 백업 ID가 필요합니다." },
            { status: 400 },
          );
        }

        const backups = await readBackups();
        const entry = backups.find((b) => b.id === body.id);
        if (!entry) {
          return NextResponse.json(
            { error: "백업을 찾을 수 없습니다." },
            { status: 404 },
          );
        }

        const backupPath = getDataPath("backups", entry.filename);
        try {
          await unlink(backupPath);
        } catch (error) {
          if (!isNotFoundError(error)) {
            throw error;
          }
        }

        const nextBackups = backups.filter((b) => b.id !== body.id);
        await saveBackups(nextBackups);

        return NextResponse.json({ success: true, backups: nextBackups });
      }

      default: {
        return NextResponse.json(
          { error: `알 수 없는 action: ${action}` },
          { status: 400 },
        );
      }
    }
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "백업 작업을 처리하지 못했습니다.",
      },
      { status: 500 },
    );
  }
}
