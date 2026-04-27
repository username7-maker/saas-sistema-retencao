import { expect, test } from "@playwright/test";

async function mockNotifications(page: import("@playwright/test").Page) {
  let markReadCalled = false;

  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "a1",
        gym_id: "11111111-1111-1111-1111-111111111111",
        full_name: "Owner Teste",
        email: "owner@test.com",
        role: "owner",
        is_active: true,
        created_at: new Date().toISOString(),
      }),
    }),
  );

  await page.route("**/api/v1/notifications/notif-1/read", (route) => {
    markReadCalled = true;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "notif-1",
        member_id: "member-1",
        user_id: null,
        title: "Aluno sem treino ha 14 dias",
        message: "Ativar plano de retencao",
        category: "retention",
        read_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        extra_data: {},
      }),
    });
  });

  await page.route("**/api/v1/notifications**", (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "notif-1",
            member_id: "member-1",
            user_id: null,
            title: "Aluno sem treino ha 14 dias",
            message: "Ativar plano de retencao",
            category: "retention",
            read_at: null,
            created_at: new Date().toISOString(),
            extra_data: {},
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      }),
    });
  });

  return {
    wasMarkReadCalled: () => markReadCalled,
  };
}

test("notifications page lists items and marks read", async ({ page }) => {
  const controls = await mockNotifications(page);
  await page.addInitScript(() => {
    localStorage.setItem("ai_gym_access_token", "token");
    localStorage.setItem("ai_gym_refresh_token", "refresh");
  });

  await page.goto("/notifications");
  await expect(page.getByRole("heading", { name: /Notifica/i })).toBeVisible();
  await expect(page.getByText("Aluno sem treino ha 14 dias")).toBeVisible();

  await page.getByRole("button", { name: "Marcar como lida" }).click();
  await expect.poll(() => controls.wasMarkReadCalled()).toBeTruthy();
});
