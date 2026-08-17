import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import {
  getPromptFilePath,
  getPromptCategoriesPath,
  isPromptSectionId,
  PROMPT_SECTION_KEYS,
  readPromptCategoryConfig,
  readPromptBox,
  readPromptSections,
  savePromptCategoryConfig,
  savePromptBox,
  savePromptSections,
} from "@/lib/prompt-store";

type PromptRequestBody = {
  assignments?: unknown;
  categories?: unknown;
  promptBox?: unknown;
  sections?: unknown;
};

export const runtime = "nodejs";

export async function GET(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  return NextResponse.json({
    promptBox: await readPromptBox(),
    sections: await readPromptSections(),
    ...(await readPromptCategoryConfig()),
    keys: PROMPT_SECTION_KEYS,
    path: getPromptFilePath(),
    categoryPath: getPromptCategoriesPath(),
  });
}

export async function POST(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) {
    return authError;
  }

  const body = (await request.json()) as PromptRequestBody;
  const shouldSaveCategories =
    body.categories !== undefined || body.assignments !== undefined;

  const saveCategories = async () =>
    shouldSaveCategories
      ? savePromptCategoryConfig({
          categories: body.categories,
          assignments: body.assignments,
        })
      : readPromptCategoryConfig();

  if (body.sections !== undefined) {
    if (!isPromptSectionsBody(body.sections)) {
      return NextResponse.json(
        { error: "sections는 프롬프트 섹션 문자열 객체여야 합니다." },
        { status: 400 },
      );
    }

    try {
      const [saved, categoryConfig] = await Promise.all([
        savePromptSections(body.sections),
        saveCategories(),
      ]);
      return NextResponse.json({
        promptBox: saved.promptBox,
        sections: saved.sections,
        ...categoryConfig,
        keys: PROMPT_SECTION_KEYS,
        path: getPromptFilePath(),
        categoryPath: getPromptCategoriesPath(),
      });
    } catch (error) {
      return NextResponse.json(
        {
          error:
            error instanceof Error
              ? error.message
              : "프롬프트를 저장하지 못했습니다.",
        },
        { status: 400 },
      );
    }
  }

  if (shouldSaveCategories && body.promptBox === undefined) {
    try {
      const [sections, promptBox, categoryConfig] = await Promise.all([
        readPromptSections(),
        readPromptBox(),
        saveCategories(),
      ]);

      return NextResponse.json({
        promptBox,
        sections,
        ...categoryConfig,
        keys: PROMPT_SECTION_KEYS,
        path: getPromptFilePath(),
        categoryPath: getPromptCategoriesPath(),
      });
    } catch (error) {
      return NextResponse.json(
        {
          error:
            error instanceof Error
              ? error.message
              : "프롬프트 카테고리를 저장하지 못했습니다.",
        },
        { status: 400 },
      );
    }
  }

  if (typeof body.promptBox !== "string") {
    return NextResponse.json(
      { error: "promptBox는 문자열이거나 sections가 제공되어야 합니다." },
      { status: 400 },
    );
  }

  try {
    const [saved, categoryConfig] = await Promise.all([
      savePromptBox(body.promptBox),
      saveCategories(),
    ]);
    return NextResponse.json({
      promptBox: saved.promptBox,
      sections: saved.sections,
      ...categoryConfig,
      keys: PROMPT_SECTION_KEYS,
      path: getPromptFilePath(),
      categoryPath: getPromptCategoriesPath(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "프롬프트를 저장하지 못했습니다.",
      },
      { status: 400 },
    );
  }
}

function isPromptSectionsBody(
  value: unknown,
): value is Partial<Record<string, string>> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  return Object.entries(value as Record<string, unknown>).every(
    ([key, sectionValue]) =>
      isPromptSectionId(key) && typeof sectionValue === "string",
  );
}
