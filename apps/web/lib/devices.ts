import { ApiRequestError, buildApiUrl, createApiRequestError } from "@/lib/api";
import { csrfHeaders } from "@/lib/csrf";
import type { Device } from "@/types/device";
import type { PublicAccessStatus } from "@/types/emergency-profile";

function createActivateDeviceRequestError(status: number): ApiRequestError {
  if (status === 400) {
    return new ApiRequestError("Identificador no disponible para activación.", status);
  }

  if (status === 401) {
    return new ApiRequestError("Sesión expirada o no autenticada.", status);
  }

  if (status === 403) {
    return new ApiRequestError("Debes verificar tu correo antes de realizar esta acción.", status);
  }

  if (status === 404) {
    return new ApiRequestError("Identificador no encontrado.", status);
  }

  return new ApiRequestError("No se pudo activar el dispositivo.", status);
}

function createActivateDeviceWithClaimCodeRequestError(status: number): ApiRequestError {
  // 400 y 404 se tratan como el mismo rechazo genérico de activación: el
  // backend ya no debería usar 404 para credential/state mismatch (D2,
  // enumeration hardening), pero el frontend no debe reintroducir esa
  // distinción si una regresión futura lo hiciera (defense in depth).
  if (status === 400 || status === 404) {
    return new ApiRequestError("Datos de activación inválidos.", status);
  }

  if (status === 401) {
    return new ApiRequestError("Sesión expirada o no autenticada.", status);
  }

  if (status === 403) {
    return new ApiRequestError("Debes verificar tu correo antes de realizar esta acción.", status);
  }

  if (status === 422) {
    return new ApiRequestError("Código de activación inválido o incompleto.", status);
  }

  if (status === 429) {
    return new ApiRequestError("Demasiados intentos. Intenta nuevamente más tarde.", status);
  }

  return new ApiRequestError("No se pudo activar el identificador.", status);
}

function createPublicAccessStatusRequestError(status: number): ApiRequestError {
  if (status === 401) {
    return new ApiRequestError("Sesión expirada o no autenticada.", status);
  }

  if (status === 404) {
    return new ApiRequestError("Identificador no encontrado.", status);
  }

  if (status === 409) {
    return new ApiRequestError("Error de integridad del perfil de emergencia.", status);
  }

  return new ApiRequestError("No se pudo consultar el estado del identificador.", status);
}

/**
 * "¿Este identificador concreto puede exponer actualmente el perfil?".
 * No es ProfileReadiness: un Device inoperativo no implica un perfil
 * incompleto, y un perfil incompleto no se deriva desde aquí.
 */
export async function getDevicePublicAccessStatus(deviceId: string): Promise<PublicAccessStatus> {
  const url = buildApiUrl(`/api/devices/${encodeURIComponent(deviceId)}/public-access-status`);

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      credentials: "include",
    });
  } catch (error) {
    throw new Error("No se pudo consultar el estado del identificador.", { cause: error });
  }

  if (!response.ok) {
    throw createPublicAccessStatusRequestError(response.status);
  }

  return (await response.json()) as PublicAccessStatus;
}

export async function getMyDevices(): Promise<Device[]> {
  const url = buildApiUrl("/api/devices");

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      credentials: "include",
    });
  } catch (error) {
    throw new Error("No se pudieron consultar los dispositivos.", { cause: error });
  }

  if (!response.ok) {
    throw createApiRequestError("No se pudieron consultar los dispositivos", response.status);
  }

  return (await response.json()) as Device[];
}

export async function activateDevice(publicId: string): Promise<Device> {
  const url = buildApiUrl("/api/devices/activate");

  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        ...csrfHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        public_id: publicId,
      }),
    });
  } catch {
    throw new ApiRequestError("No se pudo activar el dispositivo.", 0);
  }

  if (!response.ok) {
    throw createActivateDeviceRequestError(response.status);
  }

  return (await response.json()) as Device;
}

export async function activateDeviceWithClaimCode(
  publicId: string,
  claimCode: string,
): Promise<Device> {
  const url = buildApiUrl("/api/devices/activate");

  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        ...csrfHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        public_id: publicId,
        claim_code: claimCode,
      }),
    });
  } catch {
    throw new ApiRequestError("No se pudo activar el identificador.", 0);
  }

  if (!response.ok) {
    throw createActivateDeviceWithClaimCodeRequestError(response.status);
  }

  try {
    return (await response.json()) as Device;
  } catch {
    throw new ApiRequestError("No se pudo activar el identificador.", response.status);
  }
}
