import { ApiRequestError, buildApiUrl, createApiRequestError } from "@/lib/api";
import type { AuthUser, LoginRequest, LoginResponse, RegisterRequest, RegisterResponse } from "@/types/auth";

export async function login(email: string, password: string): Promise<LoginResponse> {
  const url = buildApiUrl("/api/auth/login");
  const credentials: LoginRequest = { email, password };

  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(credentials),
    });
  } catch (error) {
    throw new Error("No se pudo iniciar sesion.", { cause: error });
  }

  if (response.status === 401) {
    throw new ApiRequestError("Credenciales invalidas.", response.status);
  }

  if (!response.ok) {
    throw createApiRequestError("No se pudo iniciar sesion", response.status);
  }

  return (await response.json()) as LoginResponse;
}

export async function register(payload: RegisterRequest): Promise<AuthUser> {
  const url = buildApiUrl("/api/auth/register");

  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error("No se pudo crear la cuenta.", { cause: error });
  }

  if (response.status === 400 || response.status === 422) {
    throw new ApiRequestError("Datos de registro inválidos.", response.status);
  }

  if (response.status === 409) {
    throw new ApiRequestError("Ya existe una cuenta con este correo.", response.status);
  }

  if (!response.ok) {
    throw new ApiRequestError("No se pudo crear la cuenta.", response.status);
  }

  return (await response.json()) as RegisterResponse;
}

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
