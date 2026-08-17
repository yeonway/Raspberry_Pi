import type { Metadata, Viewport } from "next";
import { DEFAULT_THEME_ID, THEME_STORAGE_KEY, zetaThemes } from "@/lib/themes";
import "./globals.css";

export const metadata: Metadata = {
  applicationName: "zeta",
  title: process.env.NEXT_PUBLIC_APP_NAME ?? "zeta",
  description: "Zeta style AI character chat UI prototype",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "zeta",
  },
  icons: {
    icon: [
      { url: "/icons/zeta-icon.svg", type: "image/svg+xml" },
      { url: "/icons/zeta-icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/zeta-icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/zeta-icon-192.png", sizes: "192x192" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#000000",
};

const themeScript = `
(() => {
  try {
    const themes = ${JSON.stringify(zetaThemes)};
    const rawSavedTheme = window.localStorage.getItem("${THEME_STORAGE_KEY}");
    const savedTheme = rawSavedTheme === "dark" ? "midnight" : rawSavedTheme === "light" ? "${DEFAULT_THEME_ID}" : rawSavedTheme;
    const theme = themes.find((item) => item.id === savedTheme) ?? themes.find((item) => item.id === "${DEFAULT_THEME_ID}") ?? themes[0];
    document.documentElement.dataset.zetaTheme = theme.id;
    document.documentElement.style.colorScheme = theme.colorScheme;
    for (const [name, value] of Object.entries(theme.variables)) {
      document.documentElement.style.setProperty(name, value);
    }
  } catch {
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {children}
      </body>
    </html>
  );
}
