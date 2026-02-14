import { test, expect } from "@playwright/test";

async function mockDashboard(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
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
    }),
  );

  await page.route("**/api/v1/dashboards/operational", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        realtime_checkins: 14,
        heatmap: [
          { weekday: 1, hour_bucket: 7, total_checkins: 12 },
          { weekday: 1, hour_bucket: 18, total_checkins: 20 },
        ],
        inactive_7d_total: 8,
        inactive_7d_items: [],
      }),
    }),
  );
}

test("operational dashboard renders key cards", async ({ page }) => {
  await mockDashboard(page);
  await page.addInitScript(() => {
    localStorage.setItem("ai_gym_access_token", "token");
    localStorage.setItem("ai_gym_refresh_token", "refresh");
  });

  await page.goto("/dashboard/operational");

  await expect(page.getByText("Dashboard Operacional")).toBeVisible();
  await expect(page.getByText("Check-ins ultima hora")).toBeVisible();
  await expect(page.getByText("14")).toBeVisible();
});
