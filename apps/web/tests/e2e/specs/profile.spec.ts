import { test, expect } from "@playwright/test";
import type { Page, Route } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";
import type { EmergencyProfile, EmergencyProfileStatus } from "@/types/emergency-profile";

function buildProfileFixture(displayName: string): EmergencyProfile {
  const now = new Date().toISOString();

  return {
    id: "11111111-1111-1111-1111-111111111111",
    display_name: displayName,
    blood_type: null,
    allergies: null,
    medical_conditions: null,
    medications: null,
    emergency_contact_name: "Contacto de prueba",
    emergency_contact_phone: "+56 9 0000 0000",
    emergency_contact_relationship: null,
    notes: null,
    is_public: false,
    medical_conditions_none: true,
    allergies_none: true,
    medications_none: true,
    public_consent_accepted_at: null,
    public_consent_version: null,
    created_at: now,
    updated_at: now,
    deleted_at: null,
  };
}

const STATUS_FIXTURE: EmergencyProfileStatus = {
  readiness: {
    is_ready: true,
    required_fields: [],
    completed_fields: [],
    missing_fields: [],
  },
  publication_eligibility: {
    profile_ready: true,
    consent_valid: false,
    can_publish: false,
    consent_version: "v1",
  },
};

/**
 * Intercepts the two GET requests `load()` fires and queues them (instead of
 * fulfilling immediately) so a test can control exactly when — and in what
 * order — each in-flight `load()` call resolves.
 */
async function interceptProfileLoadRequests(
  page: Page,
): Promise<{ profileRoutes: Route[]; statusRoutes: Route[] }> {
  const profileRoutes: Route[] = [];
  const statusRoutes: Route[] = [];

  await page.route("**/api/emergency-profile", (route) => {
    if (route.request().method() !== "GET") {
      void route.continue();
      return;
    }
    profileRoutes.push(route);
  });

  await page.route("**/api/emergency-profile/status", (route) => {
    if (route.request().method() !== "GET") {
      void route.continue();
      return;
    }
    statusRoutes.push(route);
  });

  return { profileRoutes, statusRoutes };
}

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

// No shared beforeEach here: these tests must install route interception
// BEFORE the first navigation to /dashboard/perfil, so each manages its own
// user/login/navigation instead of reusing the describe-level beforeEach
// above (which navigates before interception could be installed).
test.describe("Perfil de emergencia — stale load race protection (H1)", () => {
  test("stale load response cannot unlock the form early or overwrite the current load (race protection)", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);

    const { profileRoutes, statusRoutes } = await interceptProfileLoadRequests(page);

    await page.goto("/dashboard/perfil");

    // This app runs with React Strict Mode enabled for the app directory
    // (next.config.ts leaves `reactStrictMode` unset, which Next.js defaults
    // to `true` for /app), so a single mount reliably fires load() twice —
    // setup, cleanup, setup — against the SAME hook instance, which is
    // exactly the shared-state race this fix protects against. We wait for
    // (at least) two requests per endpoint only to know both are in flight
    // and controllable; the assertions below check observable behavior, not
    // this count.
    await expect.poll(() => profileRoutes.length).toBeGreaterThanOrEqual(2);
    await expect.poll(() => statusRoutes.length).toBeGreaterThanOrEqual(2);

    // Resolve the STALE (first, now-cleaned-up) requests first — this
    // mirrors the original bug's ordering, where an earlier load finished
    // before the truly current one.
    await profileRoutes[0].fulfill({ json: buildProfileFixture("Nombre-Viejo-Stale") });
    await statusRoutes[0].fulfill({ json: STATUS_FIXTURE });

    // Give the (now-resolved) stale response a moment to be processed if the
    // race-condition bug were present, before asserting it had no effect.
    await page.waitForTimeout(300);

    // Invariant: while the current load is still pending, the page must stay
    // in the loading state — the stale response must not unlock the form or
    // apply its data.
    await expect(page.getByText("Cargando perfil de emergencia...")).toBeVisible();
    await expect(page.locator("#profile-display-name")).not.toBeVisible();

    // Resolve the current (second mount) requests: only this response is
    // allowed to hydrate the form.
    await profileRoutes[1].fulfill({ json: buildProfileFixture("Nombre-Nuevo-Vigente") });
    await statusRoutes[1].fulfill({ json: STATUS_FIXTURE });

    await expect(page.getByText("Cargando perfil de emergencia...")).not.toBeVisible();
    await expect(page.locator("#profile-display-name")).toHaveValue("Nombre-Nuevo-Vigente");

    // The user can now safely edit — no further stale response is pending to
    // clobber their input.
    await page.locator("#profile-display-name").fill("Editado-Por-Usuario");
    await expect(page.locator("#profile-display-name")).toHaveValue("Editado-Por-Usuario");
  });

  test("a stale load error arriving after the current load succeeded must not surface or affect state", async ({
    page,
    request,
  }) => {
    const user = await createVerifiedTestUser(request);
    await loginViaApi(page.context(), user.email, user.password);

    const { profileRoutes, statusRoutes } = await interceptProfileLoadRequests(page);

    await page.goto("/dashboard/perfil");

    await expect.poll(() => profileRoutes.length).toBeGreaterThanOrEqual(2);
    await expect.poll(() => statusRoutes.length).toBeGreaterThanOrEqual(2);

    // The current (second, still-live) load succeeds first.
    await profileRoutes[1].fulfill({ json: buildProfileFixture("Nombre-Nuevo-Vigente") });
    await statusRoutes[1].fulfill({ json: STATUS_FIXTURE });

    await expect(page.getByText("Cargando perfil de emergencia...")).not.toBeVisible();
    await expect(page.locator("#profile-display-name")).toHaveValue("Nombre-Nuevo-Vigente");

    // The stale (first mount) load fails after the current load already
    // hydrated the form.
    await profileRoutes[0].fulfill({ status: 500, json: {} });
    await statusRoutes[0].fulfill({ status: 500, json: {} });

    await page.waitForTimeout(300);

    // Invariant: a stale error must not surface, and must not disturb the
    // already-hydrated, current form state.
    await expect(page.getByText("No se pudo cargar el perfil de emergencia.")).not.toBeVisible();
    await expect(page.locator("#profile-display-name")).toHaveValue("Nombre-Nuevo-Vigente");
  });
});
