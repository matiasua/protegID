import type { APIRequestContext } from "@playwright/test";

const MAILPIT_URL = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";
const API_BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:8080";

export type TestUser = {
  email: string;
  password: string;
};

function uniqueEmail(): string {
  // email-validator (used by the API's EmailStr) rejects reserved TLDs like .local/.test,
  // so we use example.com (RFC 2606) with a unique local-part per run instead.
  const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return `protegid-e2e-${uniqueId}@example.com`;
}

/** Waits for Mailpit to receive the verification email for `email` and extracts the token from its link. */
async function waitForVerificationToken(request: APIRequestContext, email: string): Promise<string> {
  const deadline = Date.now() + 15_000;

  while (Date.now() < deadline) {
    const searchResponse = await request.get(
      `${MAILPIT_URL}/api/v1/search`,
      { params: { query: `to:${email}` } },
    );
    const searchBody = await searchResponse.json();

    if (searchBody.messages_count > 0) {
      const messageId = searchBody.messages[0].ID;
      const messageResponse = await request.get(`${MAILPIT_URL}/api/v1/message/${messageId}`);
      const message = await messageResponse.json();
      const body: string = message.Text ?? message.HTML ?? "";
      const match = body.match(/[?&]token=([^&\s"<]+)/);

      if (match) {
        return decodeURIComponent(match[1]);
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error(`No se recibió el correo de verificación para ${email} dentro del tiempo esperado.`);
}

/** Registers, verifies, and returns a fresh test user via the public API + Mailpit — no shared/fixed accounts. */
export async function createVerifiedTestUser(request: APIRequestContext): Promise<TestUser> {
  const email = uniqueEmail();
  const password = "E2e-Test-Password-1!";

  const registerResponse = await request.post(`${API_BASE_URL}/api/auth/register`, {
    data: { email, password },
  });

  if (!registerResponse.ok()) {
    throw new Error(`Registro falló: ${registerResponse.status()} ${await registerResponse.text()}`);
  }

  const token = await waitForVerificationToken(request, email);

  const verifyResponse = await request.post(`${API_BASE_URL}/api/auth/verify-email`, {
    data: { token },
  });

  if (!verifyResponse.ok()) {
    throw new Error(`Verificación falló: ${verifyResponse.status()} ${await verifyResponse.text()}`);
  }

  return { email, password };
}

/** Registers but leaves the account unverified — for the "usuario sin verificar" account scenarios. */
export async function createUnverifiedTestUser(request: APIRequestContext): Promise<TestUser> {
  const email = uniqueEmail();
  const password = "E2e-Test-Password-1!";

  const registerResponse = await request.post(`${API_BASE_URL}/api/auth/register`, {
    data: { email, password },
  });

  if (!registerResponse.ok()) {
    throw new Error(`Registro falló: ${registerResponse.status()} ${await registerResponse.text()}`);
  }

  return { email, password };
}
