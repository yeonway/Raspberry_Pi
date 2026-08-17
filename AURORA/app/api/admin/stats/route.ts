export const runtime = "nodejs";

import { NextRequest, NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import { readChatLogs } from "@/lib/chat-logs";
import { readBotConfig } from "@/lib/bot-config";
import type { Character, ChatLogEntry } from "@/types/chat";

interface StatsLogEntry extends ChatLogEntry {
  model?: string;
  inputTokens?: number;
  outputTokens?: number;
  parseError?: boolean;
  output?: string;
  timestamp?: number;
}

export async function GET(request: NextRequest) {
  const authError = await getAdminAuthError(request);
  if (authError) return authError;

  const section = request.nextUrl.searchParams.get("section");

  switch (section) {
    case "quality": {
      const [chatLogs, botConfig] = await Promise.all([readChatLogs(), readBotConfig()]);

      const characters = botConfig?.characters ?? [];
      const stats = characters.map((char: Character) => {
        const charLogs = chatLogs.filter((log: StatsLogEntry) => log.characterId === char.id);
        const total = charLogs.length;
        const errors = charLogs.filter((log: StatsLogEntry) => log.error).length;
        const parseErrors = charLogs.filter((log: StatsLogEntry) => log.parseError).length;
        const totalOutputLen = charLogs.reduce(
          (sum: number, log: StatsLogEntry) => sum + ((log.output as string)?.length ?? 0),
          0,
        );
        const avgOutputLen = total > 0 ? Math.round(totalOutputLen / total) : 0;

        return {
          characterId: char.id,
          characterName: char.name,
          total,
          errors,
          parseErrors,
          avgOutputLen,
        };
      });

      return NextResponse.json({ characterStats: stats });
    }

    case "usage": {
      const chatLogs = await readChatLogs();
      const now = Date.now();
      const DAY = 86_400_000;

      const getStats = (since: number) => {
        const logs = since > 0 ? chatLogs.filter((l: StatsLogEntry) => l.timestamp! >= since) : chatLogs;
        const requests = logs.length;
        const inputTokens = logs.reduce((s: number, l: StatsLogEntry) => s + (l.inputTokens ?? 0), 0);
        const outputTokens = logs.reduce((s: number, l: StatsLogEntry) => s + (l.outputTokens ?? 0), 0);
        const failures = logs.filter((l: StatsLogEntry) => l.error).length;
        const failureRate = requests > 0 ? +(failures / requests * 100).toFixed(1) : 0;
        return { requests, inputTokens, outputTokens, failureRate };
      };

      const periods = {
        today: getStats(now - DAY),
        "7d": getStats(now - 7 * DAY),
        "30d": getStats(now - 30 * DAY),
        all: getStats(0),
      };

      const modelUsage: Record<string, number> = {};
      const characterUsage: Record<string, number> = {};
      for (const log of chatLogs) {
        const m = (log as StatsLogEntry).model;
        const c = (log as StatsLogEntry).characterId;
        if (m) modelUsage[m] = (modelUsage[m] ?? 0) + 1;
        if (c) characterUsage[c] = (characterUsage[c] ?? 0) + 1;
      }

      return NextResponse.json({ periods, modelUsage, characterUsage });
    }

    case "modelComparison": {
      const chatLogs = await readChatLogs();

      const byModel: Record<string, { requests: number; failures: number; totalTokens: number }> = {};
      for (const log of chatLogs) {
        const model = (log as StatsLogEntry).model || "unknown";
        byModel[model] ??= { requests: 0, failures: 0, totalTokens: 0 };
        byModel[model].requests++;
        if ((log as StatsLogEntry).error) byModel[model].failures++;
        byModel[model].totalTokens +=
          ((log as StatsLogEntry).inputTokens ?? 0) + ((log as StatsLogEntry).outputTokens ?? 0);
      }

      const models = Object.entries(byModel).map(([model, d]) => ({
        model,
        requests: d.requests,
        failures: d.failures,
        totalTokens: d.totalTokens,
        avgTokens: d.requests > 0 ? Math.round(d.totalTokens / d.requests) : 0,
        failureRate: d.requests > 0 ? +((d.failures / d.requests) * 100).toFixed(1) : 0,
      }));

      return NextResponse.json({ models });
    }

    default:
      return NextResponse.json({ error: "Invalid section" }, { status: 400 });
  }
}
