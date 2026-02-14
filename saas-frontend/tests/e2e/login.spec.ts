import { test, expect } from "@playwright/test";

async function mockAuthAndExecutive(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "token",
        refresh_token: "refresh",
        token_type: "bearer",
        expires_in: 900,
      }),
    });
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "a1",
        full_name: "Owner Teste",
        email: "owner@test.com",
        role: "owner",
        is_active: true,
        created_at: new Date().toISOString(),
      }),
    });
  });

  await page.route("**/api/v1/dashboards/executive", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_members: 1000,
        active_members: 850,
        mrr: 120000,
        churn_rate: 3.2,
        nps_avg: 8.1,
        risk_distribution: { green: 700, yellow: 200, red: 100 },
      }),
    });
  });

  const linePayload = JSON.stringify([
    { month: "2025-10", value: 100000, churn_rate: 2.8, ltv: 1800, growth_mom: 3.4 },
    { month: "2025-11", value: 110000, churn_rate: 3.1, ltv: 1750, growth_mom: 2.9 },
    { month: "2025-12", value: 120000, churn_rate: 3.2, ltv: 1720, growth_mom: 2.5 },
  ]);
  await page.route("**/api/v1/dashboards/mrr", (route) => route.fulfill({ status: 200, body: linePayload }));
  await page.route("**/api/v1/dashboards/churn", (route) => route.fulfill({ status: 200, body: linePayload }));
  await page.route("**/api/v1/dashboards/ltv", (route) => route.fulfill({ status: 200, body: linePayload }));
  await page.route("**/api/v1/dashboards/growth-mom", (route) => route.fulfill({ status: 200, body: linePayload }));
}

test("login flow redirects to executive dashboard", async ({ page }) => {
  await mockAuthAndExecutive(page);

  await page.goto("/login");
  await page.getByPlaceholder("gestor@academia.com").fill("owner@test.com");
  await page.getByPlaceholder("••••••••").fill("senha1234");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page).toHaveURL(/dashboard\/executive/);
  await expect(page.getByText("Dashboard Executivo")).toBeVisible();
});
