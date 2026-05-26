"""Repositorio de sesiones de autenticación."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthSession


def create_auth_session_record(
    session: Session,
    *,
    user_id: UUID,
    session_token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthSession:
    auth_session = AuthSession(
        user_id=user_id,
        session_token_hash=session_token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    session.add(auth_session)
    session.commit()
    session.refresh(auth_session)
    return auth_session


def get_auth_session_by_token_hash(
    session: Session, session_token_hash: str
) -> AuthSession | None:
    statement = select(AuthSession).where(
        AuthSession.session_token_hash == session_token_hash
    )
    return session.scalar(statement)


def revoke_auth_session_record(
    session: Session, auth_session: AuthSession, revoked_at: datetime | None = None
) -> None:
    if auth_session.revoked_at is not None:
        return

    auth_session.revoked_at = revoked_at or datetime.now(UTC)
    session.commit()
    session.refresh(auth_session)


def update_last_used_at_if_needed(
    session: Session,
    auth_session: AuthSession,
    *,
    now: datetime,
    update_interval_seconds: int,
) -> bool:
    last_used_at = auth_session.last_used_at
    if last_used_at.tzinfo is None:
        last_used_at = last_used_at.replace(tzinfo=UTC)

    if last_used_at > now - timedelta(seconds=update_interval_seconds):
        return False

    auth_session.last_used_at = now
    session.commit()
    session.refresh(auth_session)
    return True
