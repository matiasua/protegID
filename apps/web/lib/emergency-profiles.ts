import { buildApiUrl, createApiRequestError } from "@/lib/api";
import type { EmergencyProfile, EmergencyProfileInput } from "@/types/emergency-profile";

export async function getEmergencyProfile(
  deviceId: string,
  accessToken: string,
): Promise<EmergencyProfile | null> {
  const url = buildApiUrl(`/api/devices/${encodeURIComponent(deviceId)}/emergency-profile`);

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
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

export async function upsertEmergencyProfile(
  deviceId: string,
  payload: EmergencyProfileInput,
  accessToken: string,
): Promise<EmergencyProfile> {
  const url = buildApiUrl(`/api/devices/${encodeURIComponent(deviceId)}/emergency-profile`);

  let response: Response;

  try {
    response = await fetch(url, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${accessToken}`,
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
