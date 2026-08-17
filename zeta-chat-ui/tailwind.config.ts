import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        zeta: {
          bg: "rgb(var(--zeta-bg) / <alpha-value>)",
          panel: "rgb(var(--zeta-panel) / <alpha-value>)",
          panel2: "rgb(var(--zeta-panel2) / <alpha-value>)",
          line: "rgb(var(--zeta-line) / <alpha-value>)",
          text: "rgb(var(--zeta-text) / <alpha-value>)",
          muted: "rgb(var(--zeta-muted) / <alpha-value>)",
          soft: "rgb(var(--zeta-soft) / <alpha-value>)",
          accent: "rgb(var(--zeta-accent) / <alpha-value>)",
          accentSoft: "rgb(var(--zeta-accent-soft) / <alpha-value>)",
          userBubble: "rgb(var(--zeta-user-bubble) / <alpha-value>)",
          userBubbleText: "rgb(var(--zeta-user-bubble-text) / <alpha-value>)",
          assistantBubble: "rgb(var(--zeta-assistant-bubble) / <alpha-value>)",
          assistantBubbleText:
            "rgb(var(--zeta-assistant-bubble-text) / <alpha-value>)",
          buttonText: "rgb(var(--zeta-button-text) / <alpha-value>)",
        },
      },
      boxShadow: {
        zeta: "var(--zeta-shadow)",
        glow: "var(--zeta-glow)",
      },
    },
  },
  plugins: [],
};

export default config;
