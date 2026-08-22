import { test, expect } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

const ROUTES = ["/dashboard", "/dashboard/perfil", "/dashboard/protegid", "/dashboard/cuenta"] as const;

test.describe("Dashboard shell", () => {
  test.beforeEach(async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard");
  });

  test("no horizontal overflow on any of the four routes at this viewport", async ({ page }) => {
    for (const route of ROUTES) {
      await page.goto(route);
      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      );
      expect(hasHorizontalOverflow, `overflow on ${route}`).toBe(false);
    }
  });

  test("active nav item has aria-current=page and matches route", async ({ page }) => {
    await page.goto("/dashboard/perfil");
    const activeLinks = page.locator('[aria-current="page"]');
    const visibleActiveLinks = activeLinks.locator("visible=true");
    await expect(visibleActiveLinks.first()).toBeVisible();

    const count = await activeLinks.count();
    for (let i = 0; i < count; i += 1) {
      await expect(activeLinks.nth(i)).toHaveAttribute("href", "/dashboard/perfil");
    }
  });
});

test.describe("Desktop layout", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("sidebar visible, bottom nav hidden, account/logout reachable", async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard");

    const sidebar = page.getByRole("complementary");
    await expect(sidebar).toBeVisible();
    await expect(sidebar.getByRole("navigation", { name: "Navegación principal" })).toBeVisible();
    await expect(sidebar.getByRole("button", { name: /cerrar sesión/i })).toBeVisible();

    // The mobile bottom nav exists in the DOM (md:hidden) but must not be visible on desktop.
    await expect(page.locator("nav.fixed.inset-x-0.bottom-0")).toBeHidden();
  });
});

test.describe("Mobile layout", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("bottom nav visible, sidebar hidden, four destinations with adequate touch targets", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard");

    await expect(page.getByRole("complementary")).toBeHidden();

    const bottomNav = page.locator("nav.fixed.inset-x-0.bottom-0");
    await expect(bottomNav).toBeVisible();

    const links = bottomNav.getByRole("link");
    await expect(links).toHaveCount(4);

    for (let i = 0; i < 4; i += 1) {
      const box = await links.nth(i).boundingBox();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
  });
});

test.describe("Tablet layout (768x1024)", () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test("md breakpoint: sidebar already visible, bottom nav hidden, no cramped cards", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard");

    await expect(page.getByRole("complementary")).toBeVisible();
    await expect(page.locator("nav.fixed.inset-x-0.bottom-0")).toBeHidden();

    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(hasHorizontalOverflow).toBe(false);
  });
});
