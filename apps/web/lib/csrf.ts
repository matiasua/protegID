const CSRF_COOKIE_NAME = "protegid_csrf";

export function getCsrfTokenFromCookie(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [rawName, ...rawValueParts] = cookie.trim().split("=");
    if (rawName === CSRF_COOKIE_NAME) {
      return decodeURIComponent(rawValueParts.join("="));
    }
  }

  return null;
}


export function csrfHeaders(): HeadersInit {
  const csrfToken = getCsrfTokenFromCookie();
  return csrfToken ? { "X-CSRF-Token": csrfToken } : {};
}
