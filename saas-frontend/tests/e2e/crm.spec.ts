import { test, expect } from "@playwright/test";

async function mockCrm(page: import("@playwright/test").Page) {
  let patchCalled = false;

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

  await page.route("**/api/v1/crm/leads**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "lead-1",
            full_name: "Lead Teste",
            email: "lead@test.com",
            phone: null,
            source: "instagram",
            stage: "new",
            estimated_value: 320,
            acquisition_cost: 45,
            owner_id: null,
            last_contact_at: null,
            converted_member_id: null,
            notes: [],
            lost_reason: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
        total: 1,
        page: 1,
        page_size: 200,
      }),
    }),
  );

  await page.route("**/api/v1/crm/leads/lead-1", (route) =>
    route.fulfill(
      (() => {
        patchCalled = true;
        return {
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "lead-1",
            full_name: "Lead Teste",
            email: "lead@test.com",
            phone: null,
            source: "instagram",
            stage: "contact",
            estimated_value: 320,
            acquisition_cost: 45,
            owner_id: null,
            last_contact_at: new Date().toISOString(),
            converted_member_id: null,
            notes: [],
            lost_reason: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        };
      })(),
    ),
  );

  return {
    wasPatchCalled: () => patchCalled,
  };
}

test("crm kanban renders and advances lead", async ({ page }) => {
  const controls = await mockCrm(page);
  await page.addInitScript(() => {
    localStorage.setItem("ai_gym_access_token", "token");
    localStorage.setItem("ai_gym_refresh_token", "refresh");
  });

  await page.goto("/crm");
  await expect(page.getByText("CRM - Pipeline Kanban")).toBeVisible();
  await expect(page.getByText("Lead Teste")).toBeVisible();

  await page.getByRole("button", { name: "Avancar" }).click();
  await expect.poll(() => controls.wasPatchCalled()).toBeTruthy();
});
