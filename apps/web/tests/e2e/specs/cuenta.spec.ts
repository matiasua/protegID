import { test, expect } from "@playwright/test";

import { createUnverifiedTestUser, createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

test.describe("Cuenta y seguridad", () => {
  test("unverified user sees the warning state, resend CTA, and feedback after resending", async ({
    page,
    request,
  }) => {
    const user = await createUnverifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/cuenta");

    await expect(page.getByText("Correo no verificado")).toBeVisible();
    const resendButton = page.getByRole("button", { name: "Reenviar correo de verificación" });
    await expect(resendButton).toBeVisible();

    await resendButton.click();
    await expect(page.getByRole("status")).toBeVisible({ timeout: 10_000 });
  });

  test("verified user sees the success state with no resend CTA", async ({ page, request }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/cuenta");

    await expect(page.getByText("Correo verificado")).toBeVisible();
    await expect(page.getByRole("button", { name: "Reenviar correo de verificación" })).toHaveCount(0);
  });

  test("mobile: logout from Cuenta invalidates the session", async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);
    await page.goto("/dashboard/cuenta");

    const logoutButton = page.getByRole("button", { name: /cerrar sesión/i }).last();
    await logoutButton.scrollIntoViewIfNeeded();
    await logoutButton.click();

    await page.goto("/dashboard");
    await expect(page.getByText("Aún no hay una sesión activa")).toBeVisible();
  });
});
