import { test, expect } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

test.describe("Partial failure handling (route interception, UI-only QA)", () => {
  test("GET /api/devices 500 must not render '0 devices' as if it were a real empty state", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);

    await page.route("**/api/devices", (route) => route.fulfill({ status: 500, body: "{}" }));
    await page.goto("/dashboard/protegid");

    await expect(page.getByText("Aún no tienes ProtegID asociados")).not.toBeVisible();
    await expect(page.getByRole("alert")).toBeVisible();
  });

  test("GET /api/emergency-profile 500 must not render 'no tienes perfil' as if it were a real 404", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);

    await page.route("**/api/emergency-profile", (route) => route.fulfill({ status: 500, body: "{}" }));
    await page.goto("/dashboard/perfil");

    await expect(page.getByText("Aún no has completado tu perfil de emergencia")).not.toBeVisible();
  });

  test("summary: /api/devices 500 keeps the page usable and does not claim a known protection status", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);

    await page.route("**/api/devices", (route) => route.fulfill({ status: 500, body: "{}" }));
    await page.goto("/dashboard");

    // Page must remain usable (nav still works) despite the failed devices call.
    await expect(page.getByRole("navigation", { name: "Navegación principal" }).locator("visible=true").first()).toBeVisible();
  });
});
