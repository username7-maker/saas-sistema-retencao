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
  throw new Error("Usage: node capture-premium-reports-evidence.mjs --state=<state.json> --output=<dir> [--base-url=<url>]");
}

const state = JSON.parse(fs.readFileSync(statePath, "utf8").replace(/^\uFEFF/, ""));
fs.mkdirSync(outputDir, { recursive: true });

const { gym_slug: gymSlug, email, password } = state.credentials;
const memberId = state.primary_member.id;
const evaluationId = state.evaluations.current.id;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1600, height: 1200 } });
const page = await context.newPage();

async function savePdfFromResponse(responsePromise, outPath) {
  const response = await responsePromise;
  const body = await response.body();
  fs.writeFileSync(outPath, body);
}

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByPlaceholder("academia-centro").fill(gymSlug);
  await page.getByPlaceholder("gestor@academia.com").fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 30000 });

  await page.goto(`${baseUrl}/reports`, { waitUntil: "networkidle" });
  await page.locator("section h2", { hasText: "Relatorios" }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(outputDir, "reports-catalog.png"), fullPage: true });
  const executiveResponse = page.waitForResponse((response) => response.url().includes("/api/v1/reports/dashboard/executive/pdf") && response.status() === 200);
  await page.getByRole("button", { name: "Baixar PDF premium" }).first().click();
  await savePdfFromResponse(executiveResponse, path.join(outputDir, "executive-board-pack.pdf"));

  await page.goto(`${baseUrl}/assessments/members/${memberId}?tab=bioimpedancia`, { waitUntil: "networkidle" });
  await page.getByText("Relatorio premium pronto").waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(outputDir, "member-workspace-cta.png"), fullPage: true });

  await page.goto(`${baseUrl}/assessments/members/${memberId}/body-composition/${evaluationId}/report`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Resumo do aluno" }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(outputDir, "premium-report-route.png"), fullPage: true });
  await page.evaluate(() => {
    window.open = () => null;
  });
  const studentResponse = page.waitForResponse(
    (response) => response.url().includes(`/api/v1/members/${memberId}/body-composition/${evaluationId}/pdf`) && response.status() === 200,
  );
  await page.getByRole("button", { name: "Resumo do aluno" }).click();
  await savePdfFromResponse(studentResponse, path.join(outputDir, "body-composition-student-summary.pdf"));
  const technicalResponse = page.waitForResponse(
    (response) => response.url().includes(`/api/v1/members/${memberId}/body-composition/${evaluationId}/technical-pdf`) && response.status() === 200,
  );
  await page.getByRole("button", { name: "Relatorio tecnico" }).click();
  await savePdfFromResponse(technicalResponse, path.join(outputDir, "body-composition-technical-report.pdf"));

  const result = {
    base_url: baseUrl,
    member_id: memberId,
    evaluation_id: evaluationId,
    screenshots: {
      reports_catalog: path.join(outputDir, "reports-catalog.png"),
      member_workspace_cta: path.join(outputDir, "member-workspace-cta.png"),
      premium_report_route: path.join(outputDir, "premium-report-route.png"),
    },
    pdfs: {
      executive_board_pack: path.join(outputDir, "executive-board-pack.pdf"),
      student_summary: path.join(outputDir, "body-composition-student-summary.pdf"),
      technical_report: path.join(outputDir, "body-composition-technical-report.pdf"),
    },
  };

  fs.writeFileSync(path.join(outputDir, "browser-capture.json"), JSON.stringify(result, null, 2));
} finally {
  await context.close();
  await browser.close();
}
