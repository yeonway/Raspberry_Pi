import type { ResponseStyle } from "@/types/chat";

export function normalizeResponseContent(content: string, style: ResponseStyle) {
  const trimmed = content.trim();
  if (!trimmed || style.length === "long") {
    return trimmed;
  }

  const normalized = normalizeClampCandidate(trimmed);
  const maxUnits = style.length === "short" ? 2 : 3;
  const units = splitCompleteResponseUnits(normalized);
  if (units.length === 0) {
    return cleanupClampedResponse(normalized);
  }

  return cleanupClampedResponse(units.slice(0, maxUnits).join(" "));
}

export function createResponseStreamLimiter(style: ResponseStyle) {
  const maxUnits = getResponseStreamUnitLimit(style);
  let done = false;
  let emitted = "";
  let completeUnits = 0;
  let pendingStop = false;

  return {
    append(chunk: string) {
      if (done) {
        return { text: "", done: true };
      }

      if (!maxUnits) {
        emitted += chunk;
        return { text: chunk, done: false };
      }

      let output = "";
      for (const char of Array.from(normalizeStreamingClampChunk(chunk))) {
        if (
          pendingStop &&
          /\s/.test(char) &&
          hasBalancedBoundaryQuotes(emitted + output)
        ) {
          continue;
        }

        if (pendingStop && !isResponseBoundaryTrailingChar(char)) {
          if (hasBalancedBoundaryQuotes(emitted + output)) {
            done = true;
            break;
          }
          pendingStop = false;
        }

        output += char;

        if (isResponseBoundaryChar(char) && !pendingStop) {
          completeUnits += 1;
          if (completeUnits >= maxUnits) {
            pendingStop = true;
          }
        }
      }

      emitted += output;
      return { text: output, done };
    },
  };
}

export function getResponseMaxTokens(style: ResponseStyle) {
  const globalMax = getNumberEnv("CHAT_MAX_TOKENS", 8192);
  const styleMax = getNumberEnv(
    `CHAT_MAX_TOKENS_${style.length.toUpperCase()}`,
    getDefaultResponseMaxTokens(style),
  );

  return Math.min(globalMax, styleMax);
}

export function getResponseLengthContract(style: ResponseStyle) {
  switch (style.length) {
    case "short":
      return [
        "# 출력 길이",
        "단문. 1~2문장. 서술(**)로 시작. 완성된 문장으로 끝낼 것.",
      ].join("\n");
    case "medium":
      return [
        "# 출력 길이",
        "중문. 2~4문장. 서술(**)로 시작. 완성된 문장으로 끝낼 것.",
      ].join("\n");
    case "long":
      return [
        "# 출력 길이",
        "장문. 완결된 문단. 서술(**)로 시작. 반복 금지. 완성된 문장으로 끝낼 것.",
      ].join("\n");
    default:
      return "";
  }
}

function getDefaultResponseMaxTokens(style: ResponseStyle) {
  switch (style.length) {
    case "short":
      return 192;
    case "medium":
      return 512;
    case "long":
      return 1200;
    default:
      return 512;
  }
}

function getResponseStreamUnitLimit(style: ResponseStyle) {
  if (style.length === "short") {
    return 2;
  }
  if (style.length === "medium") {
    return 3;
  }
  return 0;
}

function normalizeStreamingClampChunk(content: string) {
  return content;
}

function normalizeClampCandidate(content: string) {
  return content
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanupClampedResponse(content: string) {
  let output = content.replace(/[ \t]{2,}/g, " ").trim();
  output = stripUnmatchedBoundaryQuote(output, '"');
  output = stripUnmatchedBoundaryQuote(output, "'");
  output = stripUnmatchedBoundaryQuote(output, "*");
  return output;
}

function stripUnmatchedBoundaryQuote(content: string, quote: string) {
  const quoteCount = Array.from(content).filter((char) => char === quote).length;
  if (quoteCount % 2 === 0) {
    return content;
  }
  if (content.startsWith(quote)) {
    return content.slice(1).trimStart();
  }
  if (content.endsWith(quote)) {
    return content.slice(0, -1).trimEnd();
  }
  return content;
}

function hasBalancedBoundaryQuotes(content: string) {
  return (
    hasEvenCharCount(content, '"') &&
    hasEvenCharCount(content, "'") &&
    hasEvenCharCount(content, "*") &&
    countChar(content, "“") === countChar(content, "”") &&
    countChar(content, "‘") === countChar(content, "’")
  );
}

function hasEvenCharCount(content: string, target: string) {
  return countChar(content, target) % 2 === 0;
}

function countChar(content: string, target: string) {
  return Array.from(content).filter((char) => char === target).length;
}

function splitCompleteResponseUnits(content: string) {
  const units: string[] = [];
  const chars = Array.from(content);
  let current = "";

  for (let index = 0; index < chars.length; index += 1) {
    const char = chars[index];
    current += char;

    if (!isResponseBoundaryChar(char)) {
      continue;
    }

    while (
      index + 1 < chars.length &&
      isResponseBoundaryTrailingChar(chars[index + 1])
    ) {
      index += 1;
      current += chars[index];
    }

    const nextUnit = current.trim();
    if (nextUnit) {
      units.push(nextUnit);
    }
    current = "";
  }

  const trailing = current.trim();
  if (trailing && units.length === 0) {
    units.push(trailing);
  }

  return units;
}

function isResponseBoundaryChar(char: string) {
  return (
    char === "." ||
    char === "!" ||
    char === "?" ||
    char === "。" ||
    char === "！" ||
    char === "？" ||
    char === "…" ||
    char === "\n"
  );
}

function isResponseBoundaryTrailingChar(char: string) {
  return (
    char === "." ||
    char === "!" ||
    char === "?" ||
    char === "。" ||
    char === "！" ||
    char === "？" ||
    char === "…" ||
    char === "\"" ||
    char === "'" ||
    char === "”" ||
    char === "’" ||
    char === ")" ||
    char === "]" ||
    char === "}" ||
    /\s/.test(char)
  );
}

function getNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}
