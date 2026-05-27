"""Servicio de tokens de acción de autenticación."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import AuthActionToken, User
from app.repositories.auth_action_tokens import (
    create_auth_action_token_record,
    get_auth_action_token_by_hash_and_purpose,
    mark_auth_action_token_used_record,
    revoke_pending_auth_action_tokens,
)

PURPOSE_EMAIL_VERIFICATION = "email_verification"


class ActionTokenInvalidError(ValueError):
    pass


class ActionTokenExpiredError(ActionTokenInvalidError):
    pass


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def generate_action_token() -> str:
    return token_urlsafe(get_settings().action_token_bytes)


def hash_action_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_action_token(
    session: Session,
    user: User,
    purpose: str,
    sent_to_email: str,
    ttl_seconds: int | None = None,
) -> tuple[AuthActionToken, str]:
    settings = get_settings()
    token = generate_action_token()
    token_hash = hash_action_token(token)
    expires_at = datetime.now(UTC) + timedelta(
        seconds=ttl_seconds or settings.email_verification_token_ttl_seconds
    )

    revoke_pending_action_tokens(session, user.id, purpose)
    token_record = create_auth_action_token_record(
        session,
        user_id=user.id,
        purpose=purpose,
        token_hash=token_hash,
        sent_to_email=_normalize_email(sent_to_email),
        expires_at=expires_at,
    )
    return token_record, token


def get_action_token_by_raw_token(
    session: Session, raw_token: str, purpose: str
) -> AuthActionToken | None:
    if not raw_token:
        return None

    return get_auth_action_token_by_hash_and_purpose(
        session, hash_action_token(raw_token), purpose
    )


def validate_action_token(
    session: Session, raw_token: str, purpose: str
) -> AuthActionToken:
    token_record = get_action_token_by_raw_token(session, raw_token, purpose)
    if token_record is None:
        raise ActionTokenInvalidError("Action token is invalid")

    if token_record.used_at is not None or token_record.revoked_at is not None:
        raise ActionTokenInvalidError("Action token is invalid")

    if _as_utc(token_record.expires_at) <= datetime.now(UTC):
        raise ActionTokenExpiredError("Action token is expired")

    return token_record


def mark_action_token_used(
    session: Session, token_record: AuthActionToken
) -> None:
    mark_auth_action_token_used_record(session, token_record)


def revoke_pending_action_tokens(
    session: Session, user_id: UUID, purpose: str
) -> int:
    return revoke_pending_auth_action_tokens(
        session,
        user_id=user_id,
        purpose=purpose,
    )
