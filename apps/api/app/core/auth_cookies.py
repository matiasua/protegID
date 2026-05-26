"""Helpers de cookies de sesión de autenticación."""

from fastapi import Response

from app.core.settings import get_settings


def _get_cookie_samesite() -> str:
    samesite = get_settings().session_cookie_samesite.strip().lower()
    if samesite == "strict":
        return "Strict"
    if samesite == "none":
        return "None"

    return "Lax"


def set_auth_session_cookie(response: Response, token: str, max_age: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=_get_cookie_samesite(),
        path=settings.session_cookie_path,
    )


def clear_auth_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=_get_cookie_samesite(),
        path=settings.session_cookie_path,
    )
