import { expect, test } from "@playwright/test";

const BACKEND = "http://127.0.0.1:11972";
const FRONTEND = "http://127.0.0.1:11973";

test("backend health returns 200", async ({ request }) => {
  const resp = await request.get(`${BACKEND}/api/health`);
  expect(resp.status()).toBe(200);
  const body = await resp.json();
  expect(body).toHaveProperty("status", "ok");
});

test("frontend SPA loads without console errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto(FRONTEND);
  await expect(page.locator("#root")).toBeAttached();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();

  expect(errors).toEqual([]);
});

test("all sidebar nav routes render without 404s or console errors", async ({
  page,
}) => {
  const routes = [
    ["dashboard-page", "#/"],
    ["documents-page", "#/documents"],
    ["tools-page", "#/tools"],
    ["skills-page", "#/skills"],
    ["chat-page", "#/chat"],
    ["apps-page", "#/apps"],
    ["onboarding-page", "#/onboarding"],
    ["settings-page", "#/settings"],
    ["help-page", "#/help"],
    ["logs-page", "#/logs"],
  ] as const;

  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  for (const [testId, hash] of routes) {
    await page.goto(`${FRONTEND}/${hash}`);
    await expect(page.getByTestId(testId)).toBeVisible();
  }

  expect(errors).toEqual([]);
});

test("dashboard shows the onboarding CTA when not configured", async ({
  page,
}) => {
  await page.goto(FRONTEND);
  await expect(page.getByTestId("onboarding-cue")).toBeVisible();
});
