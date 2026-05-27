"""Repositorio de tokens de acción de autenticación."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import AuthActionToken


def create_auth_action_token_record(
    session: Session,
    *,
    user_id: UUID,
    purpose: str,
    token_hash: str,
    sent_to_email: str,
    expires_at: datetime,
) -> AuthActionToken:
    auth_action_token = AuthActionToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=token_hash,
        sent_to_email=sent_to_email,
        expires_at=expires_at,
    )
    session.add(auth_action_token)
    session.commit()
    session.refresh(auth_action_token)
    return auth_action_token


def get_auth_action_token_by_hash_and_purpose(
    session: Session, token_hash: str, purpose: str
) -> AuthActionToken | None:
    statement = select(AuthActionToken).where(
        AuthActionToken.token_hash == token_hash,
        AuthActionToken.purpose == purpose,
    )
    return session.scalar(statement)


def mark_auth_action_token_used_record(
    session: Session,
    token_record: AuthActionToken,
    used_at: datetime | None = None,
) -> None:
    if token_record.used_at is not None:
        return

    token_record.used_at = used_at or datetime.now(UTC)
    session.commit()
    session.refresh(token_record)


def revoke_pending_auth_action_tokens(
    session: Session,
    *,
    user_id: UUID,
    purpose: str,
    revoked_at: datetime | None = None,
) -> int:
    statement = (
        update(AuthActionToken)
        .where(
            AuthActionToken.user_id == user_id,
            AuthActionToken.purpose == purpose,
            AuthActionToken.used_at.is_(None),
            AuthActionToken.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at or datetime.now(UTC))
    )
    result = session.execute(statement)
    session.commit()
    return result.rowcount or 0
