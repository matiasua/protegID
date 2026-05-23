const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

export function buildApiUrl(path: `/${string}`): string {
  return `${apiBaseUrl}${path}`;
}
