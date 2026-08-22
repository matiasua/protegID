import { test, expect } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

test.describe("Resumen — protection status scenarios", () => {
  test("A. no profile yet: neutral 'sin ficha' state with create-profile CTA", async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard");

    await expect(page.getByText("Aún no tienes tu ficha de emergencia.")).toBeVisible();
    await expect(page.getByRole("link", { name: "Crear perfil" })).toBeVisible();
  });

  test("B. incomplete profile: shows missing-fields count, not a 'ready' or 'public' message", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/perfil");
    await page.locator("#profile-display-name").fill("Perfil Incompleto");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText("Guardado")).toBeVisible();

    await page.goto("/dashboard");
    await expect(page.getByText(/Completa \d+ datos? para dejar tu perfil listo\./)).toBeVisible();
    await expect(page.getByText("Tu perfil está listo para publicar.")).not.toBeVisible();
  });

  test("D. READY + PRIVATE: must say 'listo para publicar', never 'incompleto'", async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/perfil");

    await page.locator("#profile-display-name").fill("Perfil Completo");
    await page.locator("#profile-emergency-contact-name").fill("Contacto Completo");
    await page.locator("#profile-emergency-contact-phone").fill("+56 9 8765 4321");
    await page.locator("#profile-allergies-none").check();
    await page.locator("#profile-medical-conditions-none").check();
    await page.locator("#profile-medications-none").check();
    await page.locator("#profile-consent").check();
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText("Guardado")).toBeVisible();

    await page.goto("/dashboard");
    await expect(page.getByText("Tu perfil está listo para publicar.")).toBeVisible();
    await expect(page.getByText(/incompleto/i)).not.toBeVisible();
    await expect(page.getByText(/Completa \d+/)).not.toBeVisible();
  });
});
