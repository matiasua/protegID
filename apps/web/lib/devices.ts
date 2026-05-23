import { buildApiUrl, createApiRequestError } from "@/lib/api";
import type { Device } from "@/types/device";

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
