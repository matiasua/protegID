import { ApiRequestError, buildApiUrl } from "@/lib/api";
import type { PublicDeviceActivationStatus } from "@/types/public-device";

const ACTIVATION_STATUS_ERROR_MESSAGE = "No se pudo consultar el estado del identificador.";

export async function getPublicDeviceActivationStatus(
  publicId: string,
): Promise<PublicDeviceActivationStatus | null> {
  const url = buildApiUrl(`/api/public/devices/${encodeURIComponent(publicId)}/activation-status`);

  let response: Response;

  try {
    response = await fetch(url, { cache: "no-store" });
  } catch {
    throw new ApiRequestError(ACTIVATION_STATUS_ERROR_MESSAGE, 0);
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new ApiRequestError(ACTIVATION_STATUS_ERROR_MESSAGE, response.status);
  }

  try {
    return (await response.json()) as PublicDeviceActivationStatus;
  } catch {
    throw new ApiRequestError(ACTIVATION_STATUS_ERROR_MESSAGE, response.status);
  }
}
