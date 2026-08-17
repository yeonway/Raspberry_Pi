import { NextResponse } from "next/server";
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

  const adminToken = process.env.ADMIN_TOKEN;

  if (!adminToken) {
    return NextResponse.json(
      { error: "ADMIN_TOKEN이 서버에 설정되어 있지 않습니다." },
      { status: 503 },
    );
  }

  const token = request.headers
    .get("authorization")
    ?.replace(/^Bearer\s+/i, "");
  if (token !== adminToken) {
    return NextResponse.json(
      { error: "관리자 인증이 필요합니다." },
      { status: 401 },
    );
  }

  return null;
}
