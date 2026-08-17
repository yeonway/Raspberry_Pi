import { NextResponse } from "next/server";
import { getCurrentUser, updateUserProfile } from "@/lib/auth";

export const runtime = "nodejs";

type ProfileBody = {
  name?: unknown;
};

export async function PATCH(request: Request) {
  const user = await getCurrentUser(request);
  if (!user) {
    return NextResponse.json(
      { error: "로그인이 필요합니다." },
      { status: 401 },
    );
  }

  try {
    const body = (await request.json().catch(() => null)) as ProfileBody | null;
    if (typeof body?.name !== "string") {
      return NextResponse.json(
        { error: "이름을 입력하세요." },
        { status: 400 },
      );
    }

    const nextUser = await updateUserProfile({
      userId: user.id,
      name: body.name,
    });

    return NextResponse.json({ user: nextUser });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "계정 설정 저장에 실패했습니다.",
      },
      { status: 400 },
    );
  }
}
