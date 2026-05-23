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

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export function createApiRequestError(action: string, status: number): ApiRequestError {
  if (status === 401 || status === 403) {
    return new ApiRequestError("No autorizado para realizar esta operacion.", status);
  }

  return new ApiRequestError(`${action}. Estado: ${status}`, status);
}
