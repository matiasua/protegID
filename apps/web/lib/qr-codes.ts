import { ApiRequestError, buildApiUrl } from "@/lib/api";
import type { DeviceQrMetadata, DeviceQrStatus } from "@/types/qr-code";

function createDeviceQrRequestError(status: number): ApiRequestError {
  if (status === 401) {
    return new ApiRequestError("Sesion no autenticada o expirada.", status);
  }

  if (status === 403) {
    return new ApiRequestError("Se requiere rol admin para gestionar QR.", status);
  }

  if (status === 404) {
    return new ApiRequestError("Dispositivo no encontrado.", status);
  }

  return new ApiRequestError("No se pudo completar la operacion de QR.", status);
}

function createDeviceQrDownloadRequestError(status: number): ApiRequestError {
  if (status === 401) {
    return new ApiRequestError("Sesion no autenticada o expirada.", status);
  }

  if (status === 403) {
    return new ApiRequestError("Se requiere rol admin para descargar QR.", status);
  }

  if (status === 404) {
    return new ApiRequestError("QR o dispositivo no encontrado.", status);
  }

  return new ApiRequestError("No se pudo descargar el QR.", status);
}

export async function getDeviceQrStatus(
  deviceId: string,
): Promise<DeviceQrStatus> {
  const url = buildApiUrl(`/api/admin/devices/${encodeURIComponent(deviceId)}/qr`);

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      credentials: "include",
    });
  } catch {
    throw new ApiRequestError("No se pudo consultar el estado del QR.", 0);
  }

  if (!response.ok) {
    throw createDeviceQrRequestError(response.status);
  }

  return (await response.json()) as DeviceQrStatus;
}

export async function createDeviceQr(
  deviceId: string,
): Promise<DeviceQrMetadata> {
  const url = buildApiUrl(`/api/admin/devices/${encodeURIComponent(deviceId)}/qr`);

  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    throw new ApiRequestError("No se pudo generar el QR.", 0);
  }

  if (!response.ok) {
    throw createDeviceQrRequestError(response.status);
  }

  return (await response.json()) as DeviceQrMetadata;
}

export async function downloadDeviceQr(
  deviceId: string,
): Promise<Blob> {
  const url = buildApiUrl(
    `/api/admin/devices/${encodeURIComponent(deviceId)}/qr/download`,
  );

  let response: Response;

  try {
    response = await fetch(url, {
      cache: "no-store",
      credentials: "include",
    });
  } catch {
    throw new ApiRequestError("No se pudo descargar el QR.", 0);
  }

  if (!response.ok) {
    throw createDeviceQrDownloadRequestError(response.status);
  }

  return response.blob();
}
