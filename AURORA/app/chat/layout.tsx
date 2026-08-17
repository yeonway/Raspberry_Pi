"use client";

import { useEffect } from "react";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    document.documentElement.style.fontSize = "24px";
    return () => {
      document.documentElement.style.fontSize = "";
    };
  }, []);

  return <>{children}</>;
}
