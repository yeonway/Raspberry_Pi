(() => {
  const THEME_KEY = "memo:theme";
  const THEMES = new Set(["light", "dark"]);

  function preferredTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (THEMES.has(saved)) return saved;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function setTheme(theme, persist = false) {
    const nextTheme = THEMES.has(theme) ? theme : "light";
    document.documentElement.dataset.theme = nextTheme;

    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) {
      themeColor.content = nextTheme === "dark" ? "#18212a" : "#2f6f73";
    }

    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      const isActive = button.dataset.themeChoice === nextTheme;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });

    if (persist) {
      localStorage.setItem(THEME_KEY, nextTheme);
    }
  }

  setTheme(preferredTheme());

  document.addEventListener("DOMContentLoaded", () => {
    setTheme(preferredTheme());
    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      button.addEventListener("click", () => {
        setTheme(button.dataset.themeChoice, true);
      });
    });
  });
})();
