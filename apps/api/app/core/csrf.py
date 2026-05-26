"""Helpers de protección CSRF double-submit."""

from hmac import compare_digest
from secrets import token_urlsafe

from fastapi import Request, Response

from app.core.settings import get_settings


def generate_csrf_token() -> str:
    return token_urlsafe(get_settings().csrf_token_bytes)


def _get_cookie_samesite() -> str:
    samesite = get_settings().session_cookie_samesite.strip().lower()
    if samesite == "strict":
        return "Strict"
    if samesite == "none":
        return "None"

    return "Lax"


def set_csrf_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=settings.session_absolute_ttl_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=_get_cookie_samesite(),
        path=settings.session_cookie_path,
    )


def clear_csrf_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=_get_cookie_samesite(),
        path=settings.session_cookie_path,
    )


def validate_csrf_token(request: Request) -> bool:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get(settings.csrf_header_name)

    if not cookie_token or not header_token:
        return False

    return compare_digest(cookie_token, header_token)
