import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

type LedgerEntry = {
  kind: "response" | "blocked-external";
  method: string;
  origin: "frontend" | "api" | "external";
  pathname: string;
  status?: number;
  resourceType?: string;
};

type BrowserObservation = {
  classification: "test";
  target: "sandbox";
  role: string;
  viewport: { width: number; height: number };
  defaultRoute: string;
  horizontalOverflow: boolean;
  loginMissingAssociatedLabels: number;
  externalRequestsBlocked: number;
  consoleCounts: Record<string, number>;
  pageErrorCount: number;
  network: LedgerEntry[];
  performance: Record<string, number | null>;
  accessibility: Record<string, number | boolean>;
  observations: Record<string, boolean | number | string>;
};

const frontendURL = new URL(process.env.AUDIT_FRONTEND_URL ?? "");
const apiURL = new URL(process.env.AUDIT_BACKEND_URL ?? "");
const evidenceDir = process.env.AUDIT_EVIDENCE_DIR ?? "";
const password = process.env.AUDIT_ACCOUNT_PASSWORD ?? "";
const gymSlug = "teste-auditoria-alpha";

if (!evidenceDir || !password || frontendURL.hostname !== "127.0.0.1" || apiURL.hostname !== "127.0.0.1") {
  throw new Error("Audit browser guard rejected missing credentials/evidence or non-loopback URLs");
}

const roleEmails: Record<string, string> = {
  manager: "TESTE_AUDITORIA_GESTOR@teste-auditoria.invalid",
  owner: "TESTE_AUDITORIA_ALPHA_OWNER@teste-auditoria.invalid",
  receptionist: "TESTE_AUDITORIA_ALPHA_RECEPCAO@teste-auditoria.invalid",
  trainer: "TESTE_AUDITORIA_ALPHA_PROFESSOR@teste-auditoria.invalid",
};

function normalizedPath(raw: string): string {
  const parsed = new URL(raw);
  return parsed.pathname
    .replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, ":id")
    .replace(/\/\d+(?=\/|$)/g, "/:id");
}

async function installNetworkGuard(page: Page, ledger: LedgerEntry[], consoleCounts: Record<string, number>, errors: { count: number }) {
  const allowedOrigins = new Set([frontendURL.origin, apiURL.origin]);
  page.on("console", (message) => {
    consoleCounts[message.type()] = (consoleCounts[message.type()] ?? 0) + 1;
  });
  page.on("pageerror", () => {
    errors.count += 1;
  });
  page.on("response", (response) => {
    const request = response.request();
    const parsed = new URL(response.url());
    const origin = parsed.origin === frontendURL.origin ? "frontend" : parsed.origin === apiURL.origin ? "api" : "external";
    ledger.push({
      kind: "response",
      method: request.method(),
      origin,
      pathname: normalizedPath(response.url()),
      status: response.status(),
      resourceType: request.resourceType(),
    });
  });
  await page.context().route("**/*", async (route) => {
    const request = route.request();
    const parsed = new URL(request.url());
    if (["data:", "blob:"].includes(parsed.protocol) || allowedOrigins.has(parsed.origin)) {
      await route.continue();
      return;
    }
    ledger.push({
      kind: "blocked-external",
      method: request.method(),
      origin: "external",
      pathname: parsed.pathname,
      resourceType: request.resourceType(),
    });
    await route.abort("blockedbyclient");
  });
}

async function missingAssociatedLabels(page: Page): Promise<number> {
  return page.locator("input, select, textarea").evaluateAll((controls) =>
    controls.filter((control) => {
      const id = control.getAttribute("id");
      const hasFor = Boolean(id && document.querySelector(`label[for="${CSS.escape(id)}"]`));
      return !hasFor && !control.closest("label") && !control.getAttribute("aria-label") && !control.getAttribute("aria-labelledby");
    }).length,
  );
}

async function login(page: Page, role: string, expectedRoute: string): Promise<number> {
  await page.goto("/login");
  const missingLabels = await missingAssociatedLabels(page);
  await page.getByPlaceholder("academia-centro").fill(gymSlug);
  await page.getByPlaceholder("gestor@academia.com").fill(roleEmails[role]);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(new RegExp(expectedRoute.replaceAll("/", "\\/")));
  await expect(page.locator("main")).toBeVisible();
  return missingLabels;
}

async function collectPerformance(page: Page): Promise<Record<string, number | null>> {
  return page.evaluate(() => {
    const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    const paints = performance.getEntriesByType("paint");
    const fcp = paints.find((entry) => entry.name === "first-contentful-paint");
    const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
    return {
      domContentLoadedMs: navigation ? Math.round(navigation.domContentLoadedEventEnd) : null,
      loadMs: navigation ? Math.round(navigation.loadEventEnd) : null,
      responseStartMs: navigation ? Math.round(navigation.responseStart) : null,
      fcpMs: fcp ? Math.round(fcp.startTime) : null,
      resourceCount: resources.length,
      transferBytes: Math.round(resources.reduce((total, entry) => total + (entry.transferSize || 0), 0)),
    };
  });
}

async function collectAccessibilityHeuristics(page: Page): Promise<Record<string, number | boolean>> {
  return page.evaluate(() => {
    const visible = (element: Element) => {
      const style = getComputedStyle(element);
      const box = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && box.width > 0 && box.height > 0;
    };
    const controls = [...document.querySelectorAll("button, a[href], input, select, textarea")].filter(visible);
    const unnamedControls = controls.filter((element) => {
      const text = element.textContent?.trim();
      return !text && !element.getAttribute("aria-label") && !element.getAttribute("aria-labelledby") && !(element as HTMLInputElement).placeholder;
    }).length;
    const ids = [...document.querySelectorAll("[id]")].map((element) => element.id);
    const duplicateIds = ids.length - new Set(ids).size;
    const imagesMissingAlt = [...document.querySelectorAll("img")].filter((image) => !image.hasAttribute("alt")).length;
    const smallTargets = controls.filter((element) => {
      const box = element.getBoundingClientRect();
      return box.width < 24 || box.height < 24;
    }).length;
    return {
      unnamedControls,
      duplicateIds,
      imagesMissingAlt,
      smallTargets,
      hasMainLandmark: Boolean(document.querySelector("main")),
      hasSkipLink: Boolean(document.querySelector('a[href="#main-content"]')),
      tabListCount: document.querySelectorAll('[role="tablist"]').length,
      tabCount: document.querySelectorAll('[role="tab"]').length,
    };
  });
}

async function maskAndScreenshot(page: Page, testInfo: TestInfo, label: string) {
  await page.addStyleTag({ content: "input,textarea,[contenteditable=true]{filter:blur(9px)!important}" });
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes: Text[] = [];
    while (walker.nextNode()) nodes.push(walker.currentNode as Text);
    for (const node of nodes) {
      node.nodeValue = (node.nodeValue ?? "").replace(
        /TESTE_AUDITORIA_[A-Z0-9_.+@<>/='"\-]+/gi,
        "TESTE_AUDITORIA_[MASCARADO]",
      );
    }
  });
  await page.screenshot({ path: path.join(evidenceDir, `${testInfo.project.name}-${label}.png`), fullPage: true });
}

function writeObservation(label: string, observation: BrowserObservation) {
  fs.mkdirSync(evidenceDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceDir, `${label}.json`), JSON.stringify(observation, null, 2), { encoding: "utf8" });
}

async function baseObservation(
  page: Page,
  role: string,
  expectedRoute: string,
  viewport: { width: number; height: number },
  testInfo: TestInfo,
): Promise<{ observation: BrowserObservation; ledger: LedgerEntry[] }> {
  const ledger: LedgerEntry[] = [];
  const consoleCounts: Record<string, number> = {};
  const errors = { count: 0 };
  await installNetworkGuard(page, ledger, consoleCounts, errors);
  await page.setViewportSize(viewport);
  const missingLabels = await login(page, role, expectedRoute);
  const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  const observation: BrowserObservation = {
    classification: "test",
    target: "sandbox",
    role,
    viewport,
    defaultRoute: new URL(page.url()).pathname,
    horizontalOverflow,
    loginMissingAssociatedLabels: missingLabels,
    externalRequestsBlocked: ledger.filter((entry) => entry.kind === "blocked-external").length,
    consoleCounts,
    pageErrorCount: errors.count,
    network: ledger,
    performance: await collectPerformance(page),
    accessibility: await collectAccessibilityHeuristics(page),
    observations: {},
  };
  await maskAndScreenshot(page, testInfo, `${role}-${viewport.width}x${viewport.height}`);
  return { observation, ledger };
}

test("manager desktop: auth, refresh and multiple tabs", async ({ page, context }, testInfo) => {
  const viewport = { width: 1600, height: 1000 };
  const ledger: LedgerEntry[] = [];
  const consoleCounts: Record<string, number> = {};
  const errors = { count: 0 };
  await installNetworkGuard(page, ledger, consoleCounts, errors);
  await page.setViewportSize(viewport);
  const missingLabels = await login(page, "manager", "/dashboard/executive");
  await page.reload();
  await expect(page).toHaveURL(/\/dashboard\/executive/);

  const secondTab = await context.newPage();
  await secondTab.goto("/members");
  await expect(secondTab).toHaveURL(/\/members/);
  await expect(secondTab.locator("main")).toBeVisible();
  const inertXssExecuted = await secondTab.evaluate(() => Boolean((window as Window & { __TESTE_AUDITORIA_XSS__?: unknown }).__TESTE_AUDITORIA_XSS__));

  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page).toHaveURL(/\/login/);
  const taskResponsePromise = secondTab.waitForResponse(
    (response) => response.url().includes("/api/v1/tasks") && response.request().method() === "GET",
    { timeout: 15_000 },
  );
  await secondTab.getByRole("link", { name: "Tarefas" }).click();
  const taskResponse = await taskResponsePromise;
  const tabBRetainedAccessAfterLogout = taskResponse.status() === 200;
  await secondTab.reload();
  await expect(secondTab).toHaveURL(/\/login/);

  const horizontalOverflow = await secondTab.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  const observation: BrowserObservation = {
    classification: "test",
    target: "sandbox",
    role: "manager",
    viewport,
    defaultRoute: "/dashboard/executive",
    horizontalOverflow,
    loginMissingAssociatedLabels: missingLabels,
    externalRequestsBlocked: ledger.filter((entry) => entry.kind === "blocked-external").length,
    consoleCounts,
    pageErrorCount: errors.count,
    network: ledger,
    performance: await collectPerformance(page),
    accessibility: await collectAccessibilityHeuristics(page),
    observations: {
      reloadRestoredSession: true,
      secondTabAuthenticatedViaRefreshCookie: true,
      tabBRetainedAccessAfterLogout,
      tabBRejectedAfterReload: true,
      inertXssExecuted,
    },
  };
  expect(inertXssExecuted).toBe(false);
  writeObservation("browser-manager-desktop", observation);
});
test("owner notebook: navigation, focus and semantic heuristics", async ({ page }, testInfo) => {
  const viewport = { width: 1366, height: 768 };
  const { observation } = await baseObservation(page, "owner", "/dashboard/executive", viewport, testInfo);
  await page.keyboard.press("Tab");
  observation.observations.focusMovedFromBody = await page.evaluate(() => document.activeElement !== document.body);
  await page.goto("/settings");
  await expect(page.locator("main")).toBeVisible();
  const settingsA11y = await collectAccessibilityHeuristics(page);
  observation.observations.settingsTabListCount = settingsA11y.tabListCount;
  observation.observations.settingsTabCount = settingsA11y.tabCount;
  writeObservation("browser-owner-notebook", observation);
});

test("receptionist tablet: responsive operational route", async ({ page }, testInfo) => {
  const viewport = { width: 820, height: 1180 };
  const { observation } = await baseObservation(page, "receptionist", "/dashboard/operational", viewport, testInfo);
  writeObservation("browser-receptionist-tablet", observation);
});

test("trainer mobile: responsive drawer and Escape behavior", async ({ page }, testInfo) => {
  const viewport = { width: 390, height: 844 };
  const { observation } = await baseObservation(page, "trainer", "/assessments", viewport, testInfo);
  const menu = page.getByRole("button", { name: "Open navigation menu" });
  await expect(menu).toBeVisible();
  await menu.click();
  const drawer = page.locator("aside.fixed.top-0");
  const before = await drawer.boundingBox();
  await page.keyboard.press("Escape");
  const after = await drawer.boundingBox();
  observation.observations.drawerClosedWithEscape = Boolean(before && after && after.x < before.x - 100);
  observation.observations.drawerHasDialogSemantics = (await drawer.getAttribute("role")) === "dialog";
  observation.observations.drawerCloseButtonHasAccessibleName = (await drawer.locator("header button").getAttribute("aria-label")) !== null;
  writeObservation("browser-trainer-mobile", observation);
});
