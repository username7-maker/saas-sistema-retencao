import fs from "node:fs";
import path from "node:path";
import { chromium } from "@playwright/test";

function readArg(name, fallback = null) {
  const prefix = `--${name}=`;
  const hit = process.argv.find((item) => item.startsWith(prefix));
  if (!hit) return fallback;
  return hit.slice(prefix.length);
}

const statePath = readArg("state");
const outputDir = readArg("output");
const baseUrl = readArg("base-url", "https://saas-frontend-pearl.vercel.app");

if (!statePath || !outputDir) {
  throw new Error("Usage: node capture-ai-triage-evidence.mjs --state=<state.json> --output=<dir> [--base-url=<url>]");
}

const state = JSON.parse(fs.readFileSync(statePath, "utf8").replace(/^\uFEFF/, ""));
fs.mkdirSync(outputDir, { recursive: true });

const { gym_slug: gymSlug, email, password } = state.credentials;
const retentionName = state.members.retention.full_name;
const onboardingName = state.members.onboarding.full_name;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1600, height: 1200 } });
const page = await context.newPage();

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function clickRecommendationByName(name) {
  const button = page.getByRole("button", { name: new RegExp(name, "i") }).first();
  await button.waitFor({ timeout: 90000 });
  await button.click();
}

async function approveCurrent(note) {
  const noteField = page.getByPlaceholder("Opcional: registre o racional antes de aprovar ou rejeitar.");
  if (await noteField.count()) {
    await noteField.fill(note);
  }
  await page.getByRole("button", { name: "Aprovar item" }).click();
  await page.getByRole("button", { name: "Criar task" }).waitFor({ timeout: 30000 });
}

async function prepareAction(buttonName, note) {
  const noteField = page.getByPlaceholder("Opcional: registre o contexto da acao preparada.");
  if (await noteField.count()) {
    await noteField.fill(note);
  }
  await page.getByRole("button", { name: buttonName }).waitFor({ timeout: 30000 });
  await page.getByRole("button", { name: buttonName }).click();
  await page.waitForTimeout(800);
}

async function markOutcome(buttonName, note) {
  const noteField = page.getByPlaceholder("Opcional: descreva o resultado observado.");
  if (await noteField.count()) {
    await noteField.fill(note);
  }
  await page.getByRole("button", { name: buttonName }).waitFor({ timeout: 30000 });
  await page.getByRole("button", { name: buttonName }).click();
  await page.waitForTimeout(800);
}

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByPlaceholder("academia-centro").fill(gymSlug);
  await page.getByPlaceholder("gestor@academia.com").fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForFunction(() => window.location.pathname !== "/login", { timeout: 30000 });
  await page.waitForLoadState("networkidle");

  await page.goto(`${baseUrl}/ai/triage`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "AI Triage Inbox" }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(outputDir, "ai-triage-inbox-list.png"), fullPage: true });

  await clickRecommendationByName(retentionName);
  await page.getByRole("heading", { name: new RegExp(`^${escapeRegExp(retentionName)}$`, "i") }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(outputDir, "ai-triage-retention-detail.png"), fullPage: true });
  await approveCurrent("Wave 4 pilot validation - retention recommendation approved.");
  await prepareAction("Criar task", "Wave 4 pilot validation - task prepared from AI triage.");
  await markOutcome("Marcar positivo", "Wave 4 pilot validation - retention action prepared and tracked.");
  await page.screenshot({ path: path.join(outputDir, "ai-triage-retention-approved.png"), fullPage: true });

  await clickRecommendationByName(onboardingName);
  await page.getByRole("heading", { name: new RegExp(`^${escapeRegExp(onboardingName)}$`, "i") }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(outputDir, "ai-triage-onboarding-detail.png"), fullPage: true });
  await approveCurrent("Wave 4 pilot validation - onboarding recommendation approved.");
  await prepareAction("Preparar mensagem", "Wave 4 pilot validation - outbound message prepared.");
  await markOutcome("Marcar neutro", "Wave 4 pilot validation - onboarding recommendation reviewed and prepared.");
  await page.screenshot({ path: path.join(outputDir, "ai-triage-onboarding-approved.png"), fullPage: true });

  await page.screenshot({ path: path.join(outputDir, "ai-triage-metrics.png"), fullPage: true });

  const result = {
    base_url: baseUrl,
    gym_slug: gymSlug,
    screenshots: {
      list: path.join(outputDir, "ai-triage-inbox-list.png"),
      retention_detail: path.join(outputDir, "ai-triage-retention-detail.png"),
      retention_approved: path.join(outputDir, "ai-triage-retention-approved.png"),
      onboarding_detail: path.join(outputDir, "ai-triage-onboarding-detail.png"),
      onboarding_approved: path.join(outputDir, "ai-triage-onboarding-approved.png"),
      metrics: path.join(outputDir, "ai-triage-metrics.png"),
    },
  };
  fs.writeFileSync(path.join(outputDir, "browser-capture.json"), JSON.stringify(result, null, 2));
} finally {
  await context.close();
  await browser.close();
}
