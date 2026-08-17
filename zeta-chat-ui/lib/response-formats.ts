import type {
  PromptCategory,
  ResponseFlavor,
  ResponseFlavorOption,
  ResponseLength,
  ResponseLengthOption,
  ResponseOptionConfig,
  ResponseStyle,
} from "@/types/chat";

export const DEFAULT_RESPONSE_STYLE: ResponseStyle = {
  flavor: "safe",
  length: "medium",
};

export const RESPONSE_FLAVOR_CATEGORY_IDS: Record<ResponseFlavor, string> = {
  safe: "style-simple",
  intense: "style-strong",
};

export const RESPONSE_LENGTH_CATEGORY_IDS: Record<ResponseLength, string> = {
  short: "length-short",
  medium: "length-medium",
  long: "length-long",
};

const DEFAULT_RESPONSE_FLAVOR_OPTIONS: ResponseFlavorOption[] = [
  {
    value: "safe",
    label: "착한맛",
    description: "과장 없이 차분하고 안정적인 말투로 답합니다.",
  },
  {
    value: "intense",
    label: "매운맛",
    description: "감정과 상황감을 더 분명하게 살려 답합니다.",
  },
];

const DEFAULT_RESPONSE_LENGTH_OPTIONS: ResponseLengthOption[] = [
  {
    value: "short",
    label: "단문",
    description: "핵심 위주로 1~2문장 안에서 답합니다.",
  },
  {
    value: "medium",
    label: "중문",
    description: "자연스러운 대화 길이로 2~4문장 정도 답합니다.",
  },
  {
    value: "long",
    label: "장문",
    description: "맥락과 이유를 충분히 포함해 자세히 답합니다.",
  },
];

export const RESPONSE_FLAVOR_OPTIONS = createResponseFlavorOptions();
export const RESPONSE_LENGTH_OPTIONS = createResponseLengthOptions();

export function createResponseFlavorOptions(
  labels: Partial<Record<ResponseFlavor, string>> = {},
): ResponseFlavorOption[] {
  return DEFAULT_RESPONSE_FLAVOR_OPTIONS.map((option) => ({
    ...option,
    label: labels[option.value]?.trim() || option.label,
  }));
}

export function createResponseLengthOptions(
  labels: Partial<Record<ResponseLength, string>> = {},
): ResponseLengthOption[] {
  return DEFAULT_RESPONSE_LENGTH_OPTIONS.map((option) => ({
    ...option,
    label: labels[option.value]?.trim() || option.label,
  }));
}

export function createResponseOptionConfig(
  categories: PromptCategory[] = [],
): ResponseOptionConfig {
  return {
    flavors: createResponseFlavorOptions(
      getResponseCategoryLabels(categories, RESPONSE_FLAVOR_CATEGORY_IDS),
    ),
    lengths: createResponseLengthOptions(
      getResponseCategoryLabels(categories, RESPONSE_LENGTH_CATEGORY_IDS),
    ),
  };
}

function getResponseCategoryLabels<TValue extends string>(
  categories: PromptCategory[],
  categoryIds: Record<TValue, string>,
) {
  const categoryById = new Map(categories.map((category) => [category.id, category]));
  const labels: Partial<Record<TValue, string>> = {};

  for (const value of Object.keys(categoryIds) as TValue[]) {
    labels[value] = categoryById.get(categoryIds[value])?.name;
  }

  return labels;
}

export function normalizeResponseStyle(value: unknown): ResponseStyle {
  if (!value || typeof value !== "object") {
    return DEFAULT_RESPONSE_STYLE;
  }

  const candidate = value as Partial<ResponseStyle>;
  const flavor: ResponseFlavor = RESPONSE_FLAVOR_OPTIONS.some(
    (option) => option.value === candidate.flavor,
  )
    ? (candidate.flavor as ResponseFlavor)
    : DEFAULT_RESPONSE_STYLE.flavor;
  const length: ResponseLength = RESPONSE_LENGTH_OPTIONS.some(
    (option) => option.value === candidate.length,
  )
    ? (candidate.length as ResponseLength)
    : DEFAULT_RESPONSE_STYLE.length;

  return { flavor, length };
}
