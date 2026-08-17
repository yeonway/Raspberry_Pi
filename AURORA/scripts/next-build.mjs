import { spawnSync } from "node:child_process";
import {
  existsSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";

const nextBin = path.join("node_modules", "next", "dist", "bin", "next");
const result = spawnSync(process.execPath, [nextBin, "build"], {
  env: process.env,
  stdio: "inherit",
});

if (result.status === 0) {
  ensureBuildId();
}

process.exit(result.status ?? 1);

function ensureBuildId() {
  const nextDir = ".next";
  const buildIdPath = path.join(nextDir, "BUILD_ID");
  if (existsSync(buildIdPath)) {
    return;
  }

  const staticDir = path.join(nextDir, "static");
  if (!existsSync(staticDir)) {
    return;
  }

  const buildId = readdirSync(staticDir)
    .filter((entry) => entry !== "chunks" && entry !== "css")
    .find((entry) => statSync(path.join(staticDir, entry)).isDirectory());

  if (buildId) {
    writeFileSync(buildIdPath, `${buildId}\n`, "utf8");
  }
}
