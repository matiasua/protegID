import { test, expect } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

test.describe("Mis ProtegID", () => {
  test.beforeEach(async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/protegid");
  });

  test("no devices: activation card visible, empty state shown, no QR admin actions for non-admin", async ({
    page,
  }) => {
    await expect(page.getByRole("heading", { name: "Activar identificador" })).toBeVisible();
    await expect(page.getByText("Aún no tienes ProtegID asociados")).toBeVisible();
    await expect(page.getByText(/Generar QR|Descargar QR/)).toHaveCount(0);
  });

  test("activation rejects a well-formed but nonexistent public id / claim code with a visible error, does not crash the page", async ({
    page,
  }) => {
    // Syntactically valid public_id (matches DeviceActivate.pattern) that
    // does not exist in DB: exercises the activation enumeration-hardening
    // rejection path (400 "Invalid activation data"), not Pydantic 422.
    await page.locator("#activation-public-id").fill("PID-2222222222");
    await page.locator("#activation-claim-code").fill("AAAA-BBBB-CCCC");
    await page.getByRole("button", { name: "Activar identificador" }).click();

    await expect(page.getByText("Datos de activación inválidos.")).toBeVisible({ timeout: 10_000 });
    // Page must remain usable after the failed activation attempt.
    await expect(page.getByRole("heading", { name: "Activar identificador" })).toBeVisible();
  });

  test("activation shows the same generic message for both 400 and 404 responses (defense in depth)", async ({
    page,
  }) => {
    await page.route("**/api/devices/activate", async (route) => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid activation data" }),
      });
    });

    await page.locator("#activation-public-id").fill("PID-2222222222");
    await page.locator("#activation-claim-code").fill("AAAA-BBBB-CCCC");
    await page.getByRole("button", { name: "Activar identificador" }).click();

    await expect(page.getByText("Datos de activación inválidos.")).toBeVisible({ timeout: 10_000 });

    await page.unroute("**/api/devices/activate");
    await page.route("**/api/devices/activate", async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not found" }),
      });
    });

    await page.locator("#activation-public-id").fill("PID-2222222223");
    await page.locator("#activation-claim-code").fill("AAAA-BBBB-CCCC");
    await page.getByRole("button", { name: "Activar identificador" }).click();

    await expect(page.getByText("Datos de activación inválidos.")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("heading", { name: "Activar identificador" })).toBeVisible();
  });
});
