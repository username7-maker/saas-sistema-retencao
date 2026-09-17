import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5173",
    port: 5173,
    timeout: 120_000,
    reuseExistingServer: true,
    env: {
      ...process.env,
      VITE_BIOIMPEDANCE_SCANNER_V2: "true",
      VITE_BIOIMPEDANCE_CAPTURE_GUIDE_V3: "true",
      VITE_BIOIMPEDANCE_SMART_CAPTURE_V1: "true",
    },
  },
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
