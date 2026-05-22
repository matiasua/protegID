"""Utilidades de seguridad para autenticación."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from pwdlib import PasswordHash

from app.core.settings import get_settings


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def _get_jwt_secret_key() -> str:
    secret_key = get_settings().jwt_secret_key
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    return secret_key


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expires_at}

    return jwt.encode(payload, _get_jwt_secret_key(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, _get_jwt_secret_key(), algorithms=[settings.jwt_algorithm])
