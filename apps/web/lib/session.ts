const SESSION_TOKEN_KEY = "protegid_access_token";

function getSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.sessionStorage;
}

export function getSessionToken(): string | null {
  return getSessionStorage()?.getItem(SESSION_TOKEN_KEY) ?? null;
}

export function setSessionToken(accessToken: string): void {
  getSessionStorage()?.setItem(SESSION_TOKEN_KEY, accessToken);
}

export function clearSessionToken(): void {
  getSessionStorage()?.removeItem(SESSION_TOKEN_KEY);
}
