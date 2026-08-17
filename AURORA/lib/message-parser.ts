export type ParsedSegment = {
  type: "narrative" | "dialogue" | "plain";
  text: string;
};

export function parseMessageText(raw: string, userName?: string): ParsedSegment[] {
  let text = raw;
  if (userName) {
    text = text.replace(/\{\{user\}\}/g, userName);
  } else {
    text = text.replace(/\{\{user\}\}/g, "사용자");
  }

  const segments: ParsedSegment[] = [];
  let cursor = 0;
  const len = text.length;

  while (cursor < len) {
    const boldOpen = text.indexOf("**", cursor);

    if (boldOpen === -1) {
      parseRemaining(text.slice(cursor), segments);
      break;
    }

    if (boldOpen > cursor) {
      parseRemaining(text.slice(cursor, boldOpen), segments);
    }

    const boldClose = text.indexOf("**", boldOpen + 2);
    if (boldClose === -1) {
      segments.push({ type: "plain", text: text.slice(boldOpen) });
      break;
    }

    const inner = text.slice(boldOpen + 2, boldClose);
    if (inner) {
      segments.push({ type: "narrative", text: inner });
    } else {
      segments.push({ type: "plain", text: "**" });
    }

    cursor = boldClose + 2;
  }

  return segments;
}

function parseRemaining(text: string, segments: ParsedSegment[]): void {
  if (!text) return;

  let cursor = 0;
  const len = text.length;
  const buf: string[] = [];

  while (cursor < len) {
    const quoteOpen = text.indexOf('"', cursor);

    if (quoteOpen === -1) {
      buf.push(text.slice(cursor));
      break;
    }

    if (quoteOpen > cursor) {
      buf.push(text.slice(cursor, quoteOpen));
    }

    const quoteClose = text.indexOf('"', quoteOpen + 1);
    if (quoteClose === -1) {
      buf.push(text.slice(quoteOpen));
      break;
    }

    const inner = text.slice(quoteOpen, quoteClose + 1);
    if (buf.length > 0) {
      segments.push({ type: "plain", text: buf.join("") });
      buf.length = 0;
    }
    segments.push({ type: "dialogue", text: inner });

    cursor = quoteClose + 1;
  }

  if (buf.length > 0) {
    segments.push({ type: "plain", text: buf.join("") });
  }
}

export function splitMessageLines(raw: string, userName?: string): ParsedSegment[][] {
  const lines = raw.split("\n");
  const slimmed = trimExcessEmptyLines(lines);
  return slimmed.map((line) => parseMessageText(line, userName));
}

function trimExcessEmptyLines(lines: string[]): string[] {
  const result: string[] = [];
  let emptyCount = 0;
  for (const line of lines) {
    if (line.trim() === "") {
      emptyCount++;
      if (emptyCount <= 2) result.push(line);
    } else {
      emptyCount = 0;
      result.push(line);
    }
  }
  while (result.length > 0 && result[result.length - 1].trim() === "") {
    result.pop();
  }
  return result;
}
