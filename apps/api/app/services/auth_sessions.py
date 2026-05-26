"""Servicio de sesiones de autenticación server-side."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import AuthSession
from app.repositories.auth_sessions import (
    create_auth_session_record,
    get_auth_session_by_token_hash,
    revoke_auth_session_record,
    update_last_used_at_if_needed,
)


def generate_session_token() -> str:
    return token_urlsafe(get_settings().session_token_bytes)


def hash_session_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_auth_session(
    session: Session,
    user_id: UUID,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[AuthSession, str]:
    settings = get_settings()
    token = generate_session_token()
    token_hash = hash_session_token(token)
    expires_at = datetime.now(UTC) + timedelta(
        seconds=settings.session_absolute_ttl_seconds
    )

    auth_session = create_auth_session_record(
        session,
        user_id=user_id,
        session_token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return auth_session, token


def get_active_auth_session_by_token(
    session: Session, token: str
) -> AuthSession | None:
    if not token:
        return None

    auth_session = get_auth_session_by_token_hash(session, hash_session_token(token))
    if auth_session is None or auth_session.revoked_at is not None:
        return None

    now = datetime.now(UTC)
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at <= now:
        return None

    update_last_used_at_if_needed(
        session,
        auth_session,
        now=now,
        update_interval_seconds=get_settings().session_last_used_update_interval_seconds,
    )
    return auth_session


def revoke_auth_session(session: Session, auth_session: AuthSession) -> None:
    revoke_auth_session_record(session, auth_session)


def revoke_auth_session_by_token(session: Session, token: str) -> bool:
    if not token:
        return False

    auth_session = get_auth_session_by_token_hash(session, hash_session_token(token))
    if auth_session is None:
        return False

    revoke_auth_session_record(session, auth_session)
    return True
