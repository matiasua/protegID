import { buildApiUrl } from "@/lib/api";
import type { PublicProfile } from "@/types/public-profile";

export async function getPublicProfile(publicId: string): Promise<PublicProfile | null> {
  const url = buildApiUrl(`/api/public/profiles/${encodeURIComponent(publicId)}`);

  let response: Response;

  try {
    response = await fetch(url, { cache: "no-store" });
  } catch (error) {
    throw new Error("No se pudo consultar el perfil publico.", { cause: error });
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`No se pudo consultar el perfil publico. Estado: ${response.status}`);
  }

  return (await response.json()) as PublicProfile;
}
