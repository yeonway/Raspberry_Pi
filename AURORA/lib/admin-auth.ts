import { getRateLimitError } from "@/lib/rate-limit";

export function getAdminAuthError(request: Request) {
  const rateLimitError = getRateLimitError(request, {
    keyPrefix: "admin",
    maxRequests: 60,
    windowMs: 60_000,
  });
  if (rateLimitError) {
    return rateLimitError;
  }

  return null;
}
