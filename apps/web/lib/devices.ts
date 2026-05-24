import { ApiRequestError, buildApiUrl, createApiRequestError } from "@/lib/api";
import type { Device } from "@/types/device";

function createActivateDeviceRequestError(status: number): ApiRequestError {
  if (status === 400) {
    return new ApiRequestError("Identificador no disponible para activación.", status);
  }

  if (status === 401) {
    return new ApiRequestError("Sesión expirada o no autenticada.", status);
  }

  if (status === 404) {
    return new ApiRequestError("Identificador no encontrado.", status);
  }

  return new ApiRequestError("No se pudo activar el dispositivo.", status);
}

export async function getMyDevices(accessToken: string): Promise<Device[]> {
  const url = buildApiUrl("/api/devices");

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  } catch (error) {
    throw new Error("No se pudieron consultar los dispositivos.", { cause: error });
  }

  if (!response.ok) {
    throw createApiRequestError("No se pudieron consultar los dispositivos", response.status);
  }

  return (await response.json()) as Device[];
}

export async function activateDevice(publicId: string, accessToken: string): Promise<Device> {
  const url = buildApiUrl("/api/devices/activate");

  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
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
