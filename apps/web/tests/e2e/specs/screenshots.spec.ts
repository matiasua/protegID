import { test } from "@playwright/test";

import { createVerifiedTestUser } from "../fixtures/test-user";
import { loginViaApi } from "../fixtures/session";

const ROUTES: Array<{ path: string; name: string }> = [
  { path: "/dashboard", name: "resumen" },
  { path: "/dashboard/perfil", name: "perfil" },
  { path: "/dashboard/protegid", name: "protegid" },
  { path: "/dashboard/cuenta", name: "cuenta" },
];

test.describe("Screenshots (QA evidence, not committed)", () => {
  for (const route of ROUTES) {
    test(`capture ${route.name}`, async ({ page, request }, testInfo) => {
      const user = await createVerifiedTestUser(request);
      await loginViaApi(page.context(), user.email, user.password);
      await page.goto(route.path);
      await page.waitForLoadState("networkidle");
      await page.screenshot({
        path: `qa-screenshots/${testInfo.project.name}-${route.name}.png`,
        fullPage: true,
      });
    });
  }
});
