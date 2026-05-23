import { buildApiUrl, createApiRequestError } from "@/lib/api";
import type { AuthUser } from "@/types/auth";

export async function getCurrentUser(accessToken: string): Promise<AuthUser> {
  const url = buildApiUrl("/api/auth/me");

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  } catch (error) {
    throw new Error("No se pudo validar la sesion.", { cause: error });
  }

  if (!response.ok) {
    throw createApiRequestError("No se pudo validar la sesion", response.status);
  }

  return (await response.json()) as AuthUser;
}
