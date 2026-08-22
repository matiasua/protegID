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

  test("activation rejects an invalid public id / claim code with a visible error, does not crash the page", async ({
    page,
  }) => {
    await page.locator("#activation-public-id").fill("PID-DOES-NOT-EXIST");
    await page.locator("#activation-claim-code").fill("AAAA-BBBB-CCCC");
    await page.getByRole("button", { name: "Activar identificador" }).click();

    await expect(page.getByText(/no se pudo|inválid|no encontrado|incorrecto/i)).toBeVisible({ timeout: 10_000 });
    // Page must remain usable after the failed activation attempt.
    await expect(page.getByRole("heading", { name: "Activar identificador" })).toBeVisible();
  });
});
