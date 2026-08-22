import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

const ROUTES = ["/dashboard", "/dashboard/perfil", "/dashboard/protegid", "/dashboard/cuenta"] as const;

test.describe("Accessibility — automated (axe-core)", () => {
  test.beforeEach(async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
  });

  for (const route of ROUTES) {
    test(`no WCAG A/AA violations on ${route}`, async ({ page }) => {
      await page.goto(route);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

      if (results.violations.length > 0) {
        console.log(JSON.stringify(results.violations, null, 2));
      }

      expect(results.violations, results.violations.map((v) => `${v.id}: ${v.description}`).join("\n")).toEqual([]);
    });
  }
});

test.describe("Accessibility — keyboard navigation", () => {
  test("desktop nav is reachable and operable via Tab/Enter, focus indicator visible, no keyboard trap", async ({
    page,
    request,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium-desktop", "sidebar nav only exists on desktop layout");
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard");

    // Tab through the page with a generous bound (the Next.js dev-mode overlay adds a
    // variable number of extra focusable stops ahead of the app content); confirm we
    // reach the "Perfil de emergencia" nav link and that focus keeps moving (no trap).
    const focusedTexts: string[] = [];

    for (let i = 0; i < 40; i += 1) {
      await page.keyboard.press("Tab");
      const focused = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
      focusedTexts.push(focused);

      if (focused.includes("Perfil de emergencia")) {
        break;
      }
    }

    expect(focusedTexts.some((text) => text.includes("Perfil de emergencia"))).toBe(true);
    expect(new Set(focusedTexts).size).toBeGreaterThan(1);
  });

  test("profile form fields are reachable and fillable via keyboard only", async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/perfil");

    await page.locator("#profile-display-name").focus();
    await page.keyboard.type("Teclado Ficticio");
    await expect(page.locator("#profile-display-name")).toHaveValue("Teclado Ficticio");

    await page.locator("#profile-allergies-none").focus();
    await page.keyboard.press("Space");
    await expect(page.locator("#profile-allergies-none")).toBeChecked();
  });

  test("logout button is reachable and operable via keyboard", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium-desktop", "sidebar logout button only exists on desktop layout");

    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard");

    const logoutButton = page.getByRole("complementary").getByRole("button", { name: /cerrar sesión/i });
    await logoutButton.focus();
    await page.keyboard.press("Enter");

    await page.goto("/dashboard");
    await expect(page.getByText("Aún no hay una sesión activa")).toBeVisible();
  });
});
