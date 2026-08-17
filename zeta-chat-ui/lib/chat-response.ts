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
        "# Final Output Length Contract",
        "The selected length is 단문.",
        "This overrides persona text, examples, prior assistant messages, and scene momentum.",
        "Start with one brief action, mood, or scene narration wrapped in paired asterisks, like *걱정스러운 표정으로 문가를 바라본다.* Do not return dialogue only.",
        "Return 1 to 2 compact complete sentences or lines.",
        "Prefer a complete short answer over extra description.",
        "End on a complete sentence. Do not stop mid-word, mid-particle, or mid-quote.",
      ].join("\n");
    case "medium":
      return [
        "# Final Output Length Contract",
        "The selected length is 중문.",
        "This overrides persona text, examples, prior assistant messages, and scene momentum.",
        "Start with one action, mood, or scene narration wrapped in paired asterisks, like *걱정스러운 표정으로 문가를 바라본다.* Do not return dialogue only.",
        "Return 2 to 4 complete sentences.",
        "Prefer a complete medium-length answer over extra description.",
        "End on a complete sentence. Do not stop mid-word, mid-particle, or mid-quote.",
      ].join("\n");
    case "long":
      return [
        "# Final Output Length Contract",
        "The selected length is 장문.",
        "Include action, mood, or scene narration wrapped in paired asterisks, like *걱정스러운 표정으로 문가를 바라본다.* Do not return dialogue only.",
        "Return a fuller answer with complete paragraphs, but do not ramble, loop, or repeat.",
        "Prefer a complete ending over adding one more paragraph.",
        "End on a complete sentence. Do not stop mid-word, mid-particle, or mid-quote.",
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
