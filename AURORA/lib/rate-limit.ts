import { NextResponse } from "next/server";

type RateLimitRule = {
  keyPrefix: string;
  maxRequests: number;
  windowMs: number;
};

type Bucket = {
  count: number;
  resetAt: number;
};

const buckets = new Map<string, Bucket>();
const MAX_BUCKETS = 5000;
const CLEANUP_INTERVAL_MS = 60_000;

const cleanupTimer = setInterval(() => pruneExpiredBuckets(Date.now()), CLEANUP_INTERVAL_MS);
if (typeof cleanupTimer === "object" && "unref" in cleanupTimer && typeof cleanupTimer.unref === "function") {
  cleanupTimer.unref();
}

export function getRateLimitError(request: Request, rule: RateLimitRule) {
  if (isRateLimitDisabled()) {
    return null;
  }

  const now = Date.now();
  const key = `${rule.keyPrefix}:${getClientIp(request)}`;
  const bucket = buckets.get(key);

  if (!bucket || bucket.resetAt <= now) {
    buckets.set(key, {
      count: 1,
      resetAt: now + rule.windowMs,
    });
    pruneBuckets(now);
    return null;
  }

  bucket.count += 1;
  if (bucket.count <= rule.maxRequests) {
    return null;
  }

  const retryAfterSeconds = Math.max(
    1,
    Math.ceil((bucket.resetAt - now) / 1000),
  );
  return NextResponse.json(
    { error: "Too many requests. Please wait and try again." },
    {
      status: 429,
      headers: {
        "Retry-After": String(retryAfterSeconds),
      },
    },
  );
}

function getClientIp(request: Request) {
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) {
    return forwardedFor.split(",")[0].trim() || "unknown";
  }

  return (
    request.headers.get("x-real-ip") ??
    request.headers.get("cf-connecting-ip") ??
    "unknown"
  );
}

function pruneBuckets(now: number) {
  if (buckets.size <= MAX_BUCKETS) {
    return;
  }

  pruneExpiredBuckets(now);
}

function pruneExpiredBuckets(now: number) {
  for (const [key, bucket] of buckets) {
    if (bucket.resetAt <= now) {
      buckets.delete(key);
    }
  }
}

function isRateLimitDisabled() {
  return process.env.RATE_LIMIT_DISABLED === "1";
}
