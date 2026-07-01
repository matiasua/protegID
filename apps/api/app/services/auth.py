"""Servicio de autenticación y registro."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.users import (
    create_user,
    get_user_by_email,
    mark_user_email_verified,
    update_user_email_verification_sent_at,
)
from app.schemas.user import UserCreate
from app.services.auth_action_tokens import (
    PURPOSE_EMAIL_VERIFICATION,
    create_action_token,
)
from app.services.email_delivery import (
    build_email_verification_url,
    send_email_verification_email,
)


class UserAlreadyExistsError(ValueError):
    pass


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(session: Session, user_create: UserCreate) -> User:
    email = _normalize_email(str(user_create.email))
    if get_user_by_email(session, email) is not None:
        raise UserAlreadyExistsError("User email already exists")

    password_hash = hash_password(user_create.password.get_secret_value())
    try:
        return create_user(
            session,
            email=email,
            password_hash=password_hash,
            full_name=user_create.full_name,
            role="user",
            status="active",
        )
    except IntegrityError:
        session.rollback()
        raise UserAlreadyExistsError("User email already exists") from None


def send_user_email_verification(session: Session, user: User) -> None:
    _, token = create_action_token(
        session,
        user,
        PURPOSE_EMAIL_VERIFICATION,
        user.email,
    )
    send_email_verification_email(user.email, build_email_verification_url(token))
    update_user_email_verification_sent_at(session, user)


def verify_user_email(session: Session, user: User) -> None:
    mark_user_email_verified(session, user, datetime.now(UTC))


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(session, _normalize_email(email))
    if user is None:
        return None

    if user.status != "active":
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
