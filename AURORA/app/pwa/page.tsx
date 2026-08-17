import type { Metadata } from "next";
import { PwaInstallPanel } from "@/components/pwa/PwaInstallPanel";

export const metadata: Metadata = {
  title: "앱처럼 열기",
  description: "Zeta Chat PWA 설치 및 실행",
};

export default function PwaPage() {
  return <PwaInstallPanel />;
}
