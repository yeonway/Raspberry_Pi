"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Palette } from "lucide-react";
import {
  DEFAULT_THEME_ID,
  THEME_STORAGE_KEY,
  getTheme,
  zetaThemes,
  type ZetaTheme,
} from "@/lib/themes";
import { cn } from "@/lib/utils";

type ThemeSelectorProps = {
  className?: string;
};

function readSavedTheme() {
  if (typeof window === "undefined") {
    return DEFAULT_THEME_ID;
  }

  return getTheme(window.localStorage.getItem(THEME_STORAGE_KEY)).id;
}

function applyTheme(theme: ZetaTheme) {
  const root = document.documentElement;
  root.dataset.zetaTheme = theme.id;
  root.style.colorScheme = theme.colorScheme;
  Object.entries(theme.variables).forEach(([name, value]) => {
    root.style.setProperty(name, value);
  });
  window.localStorage.setItem(THEME_STORAGE_KEY, theme.id);
}

export function ThemeSelector({ className }: ThemeSelectorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [themeId, setThemeId] = useState(DEFAULT_THEME_ID);

  useEffect(() => {
    const savedThemeId = readSavedTheme();
    const savedTheme = getTheme(savedThemeId);
    setThemeId(savedTheme.id);
    applyTheme(savedTheme);
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    window.addEventListener("pointerdown", handlePointerDown);
    return () => window.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  const selectedTheme = getTheme(themeId);

  return (
    <div className={cn("relative", className)} ref={containerRef}>
      <button
        aria-expanded={open}
        aria-label={`Select theme: ${selectedTheme.label}`}
        className="inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-zeta-line bg-zeta-panel text-zeta-muted transition hover:bg-zeta-panel2 hover:text-zeta-text"
        onClick={() => setOpen((current) => !current)}
        title="Select theme"
        type="button"
      >
        <Palette size={18} />
      </button>

      {open ? (
        <div className="absolute right-0 top-12 z-30 w-[min(86vw,22rem)] overflow-hidden rounded-lg border border-zeta-line bg-zeta-panel shadow-zeta">
          <div className="border-b border-zeta-line px-4 py-3">
            <p className="text-sm font-semibold text-zeta-text">Theme</p>
            <p className="mt-0.5 text-xs text-zeta-muted">
              Changes background, bubbles, accent, text, and font.
            </p>
          </div>
          <div className="max-h-[min(70vh,28rem)] overflow-y-auto p-2">
            {zetaThemes.map((theme) => {
              const selected = theme.id === themeId;
              return (
                <button
                  className={cn(
                    "grid w-full grid-cols-[2.75rem_minmax(0,1fr)_1.25rem] items-center gap-3 rounded-lg px-3 py-2.5 text-left transition",
                    selected
                      ? "bg-zeta-accentSoft text-zeta-text"
                      : "text-zeta-muted hover:bg-zeta-panel2 hover:text-zeta-text",
                  )}
                  key={theme.id}
                  onClick={() => {
                    setThemeId(theme.id);
                    applyTheme(theme);
                    setOpen(false);
                  }}
                  type="button"
                >
                  <span className="grid size-11 grid-cols-2 overflow-hidden rounded-full border border-zeta-line">
                    <span style={{ backgroundColor: theme.swatches.background }} />
                    <span style={{ backgroundColor: theme.swatches.accent }} />
                    <span style={{ backgroundColor: theme.swatches.assistantBubble }} />
                    <span style={{ backgroundColor: theme.swatches.userBubble }} />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold">
                      {theme.label}
                    </span>
                    <span className="mt-0.5 block truncate text-xs opacity-80">
                      {theme.description}
                    </span>
                  </span>
                  {selected ? <Check className="text-zeta-accent" size={17} /> : null}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
