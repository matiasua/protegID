function getApiBaseUrl(): string {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

  if (configuredBaseUrl) {
    return configuredBaseUrl;
  }

  return typeof window === "undefined" ? "http://protegid-api:8000" : "";
}

export function buildApiUrl(path: `/${string}`): string {
  return `${getApiBaseUrl()}${path}`;
}
