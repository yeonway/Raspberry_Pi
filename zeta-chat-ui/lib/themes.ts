export type ThemeVariable =
  | "--zeta-bg"
  | "--zeta-panel"
  | "--zeta-panel2"
  | "--zeta-line"
  | "--zeta-text"
  | "--zeta-muted"
  | "--zeta-soft"
  | "--zeta-accent"
  | "--zeta-accent-soft"
  | "--zeta-user-bubble"
  | "--zeta-user-bubble-text"
  | "--zeta-assistant-bubble"
  | "--zeta-assistant-bubble-text"
  | "--zeta-button-text"
  | "--zeta-font-family"
  | "--zeta-shadow"
  | "--zeta-glow";

export type ZetaTheme = {
  id: string;
  label: string;
  description: string;
  colorScheme: "light" | "dark";
  swatches: {
    background: string;
    accent: string;
    userBubble: string;
    assistantBubble: string;
  };
  variables: Record<ThemeVariable, string>;
};

export const THEME_STORAGE_KEY = "zeta-theme";
export const DEFAULT_THEME_ID = "violet-night";

const systemFont =
  'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const roundedFont =
  '"Segoe UI", Pretendard, ui-sans-serif, system-ui, -apple-system, sans-serif';
const serifFont =
  'Georgia, "Times New Roman", ui-serif, serif';
const monoFont =
  '"SFMono-Regular", Consolas, "Liberation Mono", ui-monospace, monospace';

export const zetaThemes = [
  {
    id: DEFAULT_THEME_ID,
    label: "Violet Night",
    description: "Dark chat bar palette with a vivid violet action color",
    colorScheme: "dark",
    swatches: {
      background: "#08080a",
      accent: "#6d2df6",
      userBubble: "#6d2df6",
      assistantBubble: "#1f1f23",
    },
    variables: {
      "--zeta-bg": "8 8 10",
      "--zeta-panel": "15 15 18",
      "--zeta-panel2": "31 31 35",
      "--zeta-line": "39 39 44",
      "--zeta-text": "240 240 245",
      "--zeta-muted": "176 176 186",
      "--zeta-soft": "125 125 136",
      "--zeta-accent": "109 45 246",
      "--zeta-accent-soft": "45 28 82",
      "--zeta-user-bubble": "109 45 246",
      "--zeta-user-bubble-text": "255 255 255",
      "--zeta-assistant-bubble": "31 31 35",
      "--zeta-assistant-bubble-text": "240 240 245",
      "--zeta-button-text": "255 255 255",
      "--zeta-font-family": roundedFont,
      "--zeta-shadow": "0 18px 44px rgba(0, 0, 0, 0.42)",
      "--zeta-glow": "0 0 0 3px rgba(109, 45, 246, 0.24)",
    },
  },
  {
    id: "zeta",
    label: "Zeta Default",
    description: "Bright background with a crisp blue chat bubble",
    colorScheme: "light",
    swatches: {
      background: "#f3f4f6",
      accent: "#2563eb",
      userBubble: "#2563eb",
      assistantBubble: "#ffffff",
    },
    variables: {
      "--zeta-bg": "243 244 246",
      "--zeta-panel": "255 255 255",
      "--zeta-panel2": "249 250 251",
      "--zeta-line": "229 231 235",
      "--zeta-text": "17 24 39",
      "--zeta-muted": "75 85 99",
      "--zeta-soft": "156 163 175",
      "--zeta-accent": "37 99 235",
      "--zeta-accent-soft": "219 234 254",
      "--zeta-user-bubble": "37 99 235",
      "--zeta-user-bubble-text": "255 255 255",
      "--zeta-assistant-bubble": "255 255 255",
      "--zeta-assistant-bubble-text": "17 24 39",
      "--zeta-button-text": "255 255 255",
      "--zeta-font-family": systemFont,
      "--zeta-shadow": "0 12px 30px rgba(15, 23, 42, 0.08)",
      "--zeta-glow": "0 0 0 3px rgba(37, 99, 235, 0.12)",
    },
  },
  {
    id: "midnight",
    label: "Midnight",
    description: "Dark panels with a muted teal accent",
    colorScheme: "dark",
    swatches: {
      background: "#15171c",
      accent: "#5eead4",
      userBubble: "#0f766e",
      assistantBubble: "#232832",
    },
    variables: {
      "--zeta-bg": "21 23 28",
      "--zeta-panel": "29 32 39",
      "--zeta-panel2": "35 40 50",
      "--zeta-line": "64 73 88",
      "--zeta-text": "248 250 252",
      "--zeta-muted": "203 213 225",
      "--zeta-soft": "148 163 184",
      "--zeta-accent": "20 184 166",
      "--zeta-accent-soft": "19 78 74",
      "--zeta-user-bubble": "15 118 110",
      "--zeta-user-bubble-text": "240 253 250",
      "--zeta-assistant-bubble": "35 40 50",
      "--zeta-assistant-bubble-text": "248 250 252",
      "--zeta-button-text": "240 253 250",
      "--zeta-font-family": systemFont,
      "--zeta-shadow": "0 18px 44px rgba(0, 0, 0, 0.38)",
      "--zeta-glow": "0 0 0 3px rgba(94, 234, 212, 0.18)",
    },
  },
  {
    id: "sakura",
    label: "Sakura",
    description: "Soft pink background with a deep rose bubble",
    colorScheme: "light",
    swatches: {
      background: "#fff1f2",
      accent: "#be123c",
      userBubble: "#be123c",
      assistantBubble: "#fffafb",
    },
    variables: {
      "--zeta-bg": "255 241 242",
      "--zeta-panel": "255 250 251",
      "--zeta-panel2": "255 228 230",
      "--zeta-line": "253 164 175",
      "--zeta-text": "76 5 25",
      "--zeta-muted": "136 19 55",
      "--zeta-soft": "190 80 111",
      "--zeta-accent": "190 18 60",
      "--zeta-accent-soft": "255 228 230",
      "--zeta-user-bubble": "190 18 60",
      "--zeta-user-bubble-text": "255 241 242",
      "--zeta-assistant-bubble": "255 250 251",
      "--zeta-assistant-bubble-text": "76 5 25",
      "--zeta-button-text": "255 241 242",
      "--zeta-font-family": roundedFont,
      "--zeta-shadow": "0 14px 34px rgba(136, 19, 55, 0.13)",
      "--zeta-glow": "0 0 0 3px rgba(190, 18, 60, 0.14)",
    },
  },
  {
    id: "forest",
    label: "Forest",
    description: "Warm green tones with calm natural contrast",
    colorScheme: "light",
    swatches: {
      background: "#f2f7ef",
      accent: "#2f6f4e",
      userBubble: "#2f6f4e",
      assistantBubble: "#fffef8",
    },
    variables: {
      "--zeta-bg": "242 247 239",
      "--zeta-panel": "255 254 248",
      "--zeta-panel2": "230 241 224",
      "--zeta-line": "177 201 164",
      "--zeta-text": "30 45 34",
      "--zeta-muted": "70 91 67",
      "--zeta-soft": "112 137 104",
      "--zeta-accent": "47 111 78",
      "--zeta-accent-soft": "213 232 203",
      "--zeta-user-bubble": "47 111 78",
      "--zeta-user-bubble-text": "250 255 247",
      "--zeta-assistant-bubble": "255 254 248",
      "--zeta-assistant-bubble-text": "30 45 34",
      "--zeta-button-text": "250 255 247",
      "--zeta-font-family": roundedFont,
      "--zeta-shadow": "0 14px 34px rgba(30, 45, 34, 0.11)",
      "--zeta-glow": "0 0 0 3px rgba(47, 111, 78, 0.16)",
    },
  },
  {
    id: "ink",
    label: "Ink",
    description: "High-contrast black and white with a mono font",
    colorScheme: "light",
    swatches: {
      background: "#f7f7f2",
      accent: "#111111",
      userBubble: "#111111",
      assistantBubble: "#ffffff",
    },
    variables: {
      "--zeta-bg": "247 247 242",
      "--zeta-panel": "255 255 255",
      "--zeta-panel2": "237 237 229",
      "--zeta-line": "31 31 31",
      "--zeta-text": "17 17 17",
      "--zeta-muted": "55 55 55",
      "--zeta-soft": "92 92 92",
      "--zeta-accent": "17 17 17",
      "--zeta-accent-soft": "231 231 224",
      "--zeta-user-bubble": "17 17 17",
      "--zeta-user-bubble-text": "255 255 255",
      "--zeta-assistant-bubble": "255 255 255",
      "--zeta-assistant-bubble-text": "17 17 17",
      "--zeta-button-text": "255 255 255",
      "--zeta-font-family": monoFont,
      "--zeta-shadow": "0 10px 0 rgba(17, 17, 17, 0.12)",
      "--zeta-glow": "0 0 0 3px rgba(17, 17, 17, 0.16)",
    },
  },
  {
    id: "paper",
    label: "Paper",
    description: "Reading-focused serif type with an ink blue bubble",
    colorScheme: "light",
    swatches: {
      background: "#fbfaf5",
      accent: "#31566b",
      userBubble: "#31566b",
      assistantBubble: "#ffffff",
    },
    variables: {
      "--zeta-bg": "251 250 245",
      "--zeta-panel": "255 255 255",
      "--zeta-panel2": "240 238 230",
      "--zeta-line": "207 201 187",
      "--zeta-text": "37 38 34",
      "--zeta-muted": "86 85 76",
      "--zeta-soft": "129 124 111",
      "--zeta-accent": "49 86 107",
      "--zeta-accent-soft": "222 234 239",
      "--zeta-user-bubble": "49 86 107",
      "--zeta-user-bubble-text": "250 253 255",
      "--zeta-assistant-bubble": "255 255 255",
      "--zeta-assistant-bubble-text": "37 38 34",
      "--zeta-button-text": "250 253 255",
      "--zeta-font-family": serifFont,
      "--zeta-shadow": "0 12px 28px rgba(37, 38, 34, 0.1)",
      "--zeta-glow": "0 0 0 3px rgba(49, 86, 107, 0.14)",
    },
  },
] as const satisfies readonly ZetaTheme[];

export type ZetaThemeId = (typeof zetaThemes)[number]["id"];

export function getTheme(themeId: string | null | undefined): ZetaTheme {
  if (themeId === "dark") {
    return getTheme("midnight");
  }

  if (themeId === "light") {
    return getTheme(DEFAULT_THEME_ID);
  }

  return zetaThemes.find((theme) => theme.id === themeId) ?? zetaThemes[0];
}
