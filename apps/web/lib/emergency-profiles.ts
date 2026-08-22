import { ApiRequestError, buildApiUrl, createApiRequestError } from "@/lib/api";
import { csrfHeaders } from "@/lib/csrf";
import type {
  EmergencyProfile,
  EmergencyProfileInput,
  EmergencyProfileStatus,
} from "@/types/emergency-profile";

/**
 * API canonica account-scoped (Bloque 6): no requiere deviceId. El perfil de
 * emergencia pertenece al usuario/ProtectedPerson, no a un Device.
 */

export async function getEmergencyProfile(): Promise<EmergencyProfile | null> {
  const url = buildApiUrl("/api/emergency-profile");

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      credentials: "include",
    });
  } catch (error) {
    throw new Error("No se pudo consultar el perfil de emergencia.", { cause: error });
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw createApiRequestError("No se pudo consultar el perfil de emergencia", response.status);
  }

  return (await response.json()) as EmergencyProfile;
}

export async function updateEmergencyProfile(
  payload: EmergencyProfileInput,
): Promise<EmergencyProfile> {
  const url = buildApiUrl("/api/emergency-profile");

  let response: Response;

  try {
    response = await fetch(url, {
      method: "PUT",
      credentials: "include",
      headers: {
        ...csrfHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error("No se pudo guardar el perfil de emergencia.", { cause: error });
  }

  if (!response.ok) {
    throw createApiRequestError("No se pudo guardar el perfil de emergencia", response.status);
  }

  return (await response.json()) as EmergencyProfile;
}

export async function getEmergencyProfileStatus(): Promise<EmergencyProfileStatus> {
  const url = buildApiUrl("/api/emergency-profile/status");

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      credentials: "include",
    });
  } catch (error) {
    throw new Error("No se pudo consultar el estado del perfil.", { cause: error });
  }

  if (response.status === 401 || response.status === 403) {
    throw new ApiRequestError("Sesión expirada o no autenticada.", response.status);
  }

  if (response.status === 404) {
    throw new ApiRequestError("Perfil de emergencia no disponible.", response.status);
  }

  if (!response.ok) {
    throw createApiRequestError("No se pudo consultar el estado del perfil", response.status);
  }

  return (await response.json()) as EmergencyProfileStatus;
}
