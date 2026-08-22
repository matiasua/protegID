import type { BrowserContext } from "@playwright/test";

const API_BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:8080";

/**
 * Logs in via the API using the browser context's own request/cookie jar, so the
 * resulting session cookie is available to subsequent page navigations without
 * going through the login form UI.
 */
export async function loginViaApi(context: BrowserContext, email: string, password: string): Promise<void> {
  const response = await context.request.post(`${API_BASE_URL}/api/auth/login`, {
    data: { email, password },
  });

  if (!response.ok()) {
    throw new Error(`Login falló: ${response.status()} ${await response.text()}`);
  }
}
