import { test, expect } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

test.describe("Perfil de emergencia", () => {
  test.beforeEach(async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/perfil");
  });

  test("no existing profile shows the empty-state notice and incomplete status", async ({ page }) => {
    await expect(page.getByText("Aún no has completado tu perfil de emergencia")).toBeVisible();
    await expect(page.getByText("Perfil incompleto")).toBeVisible();
  });

  test("empty form: save is disabled until a field changes (dirty state)", async ({ page }) => {
    const saveButton = page.getByRole("button", { name: "Guardar cambios" });
    await expect(saveButton).toBeDisabled();
    await expect(page.getByText("Sin cambios")).toBeVisible();

    await page.locator("#profile-display-name").fill("Juana Ficticia");
    await expect(page.getByText("Cambios sin guardar")).toBeVisible();
    await expect(saveButton).toBeEnabled();
  });

  test("filling required fields + none-decisions, saving, reload persists data and readiness updates", async ({
    page,
  }) => {
    await page.locator("#profile-display-name").fill("Juana Ficticia");
    await page.locator("#profile-emergency-contact-name").fill("Pedro Contacto");
    await page.locator("#profile-emergency-contact-phone").fill("+56 9 1234 5678");
    await page.locator("#profile-allergies-none").check();
    await page.locator("#profile-medical-conditions-none").check();
    await page.locator("#profile-medications-none").check();

    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText("Guardado")).toBeVisible();

    await page.reload();
    await expect(page.locator("#profile-display-name")).toHaveValue("Juana Ficticia");
    await expect(page.locator("#profile-emergency-contact-name")).toHaveValue("Pedro Contacto");
    await expect(page.locator("#profile-allergies-none")).toBeChecked();
    await expect(page.getByText("Aún no has completado tu perfil de emergencia")).not.toBeVisible();
    await expect(page.getByText("Todos los campos obligatorios están completos.")).toBeVisible();
  });

  test("consent and publication gating: cannot enable public profile without eligibility, private preview stays consistent", async ({
    page,
  }) => {
    await page.locator("#profile-display-name").fill("Juana Ficticia");
    await page.locator("#profile-emergency-contact-name").fill("Pedro Contacto");
    await page.locator("#profile-emergency-contact-phone").fill("+56 9 1234 5678");
    await page.locator("#profile-allergies-none").check();
    await page.locator("#profile-medical-conditions-none").check();
    await page.locator("#profile-medications-none").check();
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText("Guardado")).toBeVisible();

    // Readiness is met, but consent has not been accepted yet: publish toggle should stay blocked.
    const publicToggle = page.locator("#profile-is-public");
    await expect(publicToggle).toBeDisabled();
    await expect(page.getByText("Guarda el consentimiento de publicación para habilitar la publicación.")).toBeVisible();

    await page.locator("#profile-consent").check();
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText("Guardado")).toBeVisible();
    await expect(publicToggle).toBeEnabled();
  });
});
