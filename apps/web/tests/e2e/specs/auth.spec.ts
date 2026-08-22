import { test, expect } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

test.describe("Dashboard auth gate", () => {
  test("unauthenticated user hitting /dashboard sees the auth gate, not private content", async ({ page }) => {
    await page.goto("/dashboard");

    await expect(page.getByText("Aún no hay una sesión activa")).toBeVisible();
    await expect(page.getByRole("link", { name: "Ir a login" })).toBeVisible();
  });

  test("authenticated user can navigate the four private routes, then logout invalidates the session", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);

    await page.goto("/dashboard");
    await expect(page.getByText("Aún no hay una sesión activa")).not.toBeVisible();

    for (const path of ["/dashboard", "/dashboard/perfil", "/dashboard/protegid", "/dashboard/cuenta"]) {
      await page.goto(path);
      await expect(page.getByText("Aún no hay una sesión activa")).not.toBeVisible();
    }

    // The logout affordance only lives in the desktop sidebar and the Cuenta page's
    // session card; on mobile the sidebar is hidden, so route to Cuenta first.
    await page.goto("/dashboard/cuenta");
    const logoutButton = page.getByRole("button", { name: /cerrar sesión/i }).locator("visible=true").first();
    await logoutButton.click();

    await page.goto("/dashboard");
    await expect(page.getByText("Aún no hay una sesión activa")).toBeVisible();
  });
});
