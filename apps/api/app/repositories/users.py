"""Repositorio de usuarios."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(session: Session, email: str) -> User | None:
    normalized_email = _normalize_email(email)
    statement = select(User).where(func.lower(User.email) == normalized_email)
    return session.scalar(statement)


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def create_user(
    session: Session,
    *,
    email: str,
    password_hash: str,
    full_name: str | None = None,
    role: str = "user",
    status: str = "active",
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role=role,
        status=status,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
