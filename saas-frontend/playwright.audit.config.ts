import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.AUDIT_FRONTEND_URL;
const evidenceDir = process.env.AUDIT_EVIDENCE_DIR;

if (!baseURL || !evidenceDir) {
  throw new Error("AUDIT_FRONTEND_URL and AUDIT_EVIDENCE_DIR are required");
}

const parsed = new URL(baseURL);
if (parsed.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(parsed.hostname)) {
  throw new Error("Authenticated audit refuses any non-loopback frontend URL");
}

export default defineConfig({
  testDir: "./tests/audit",
  outputDir: path.join(evidenceDir, "playwright-artifacts"),
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  fullyParallel: false,
  preserveOutput: "always",
  reporter: [
    ["line"],
    ["json", { outputFile: path.join(evidenceDir, "playwright-results.json") }],
  ],
  use: {
    ...devices["Desktop Chrome"],
    baseURL,
    trace: "off",
    video: "off",
    screenshot: "off",
    serviceWorkers: "block",
    ignoreHTTPSErrors: false,
  },
});
