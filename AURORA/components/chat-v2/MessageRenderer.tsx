"use client";

import type { ParsedSegment } from "@/lib/message-parser";
import { splitMessageLines } from "@/lib/message-parser";

export function MessageRenderer({
  content,
  userName,
  narrativeClass = "italic text-zeta-soft",
  dialogueClass = "text-zeta-text font-medium",
  plainClass = "text-zeta-text",
}: {
  content: string;
  userName?: string;
  narrativeClass?: string;
  dialogueClass?: string;
  plainClass?: string;
}) {
  const lines = splitMessageLines(content, userName);

  return (
    <>
      {lines.map((segments, lineIdx) => (
        <span key={lineIdx}>
          {lineIdx > 0 ? <br /> : null}
          {segments.map((seg, segIdx) => (
            <SegmentSpan key={segIdx} seg={seg} narrativeClass={narrativeClass} dialogueClass={dialogueClass} plainClass={plainClass} />
          ))}
        </span>
      ))}
    </>
  );
}

function SegmentSpan({
  seg,
  narrativeClass,
  dialogueClass,
  plainClass,
}: {
  seg: ParsedSegment;
  narrativeClass: string;
  dialogueClass: string;
  plainClass: string;
}) {
  if (seg.type === "narrative") {
    return <span className={narrativeClass}>{seg.text}</span>;
  }
  if (seg.type === "dialogue") {
    return <span className={dialogueClass}>{seg.text}</span>;
  }
  return <span className={plainClass}>{seg.text}</span>;
}
