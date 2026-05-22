"""Servicio de autenticación y registro."""

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.users import create_user, get_user_by_email
from app.schemas.user import UserCreate


class UserAlreadyExistsError(ValueError):
    pass


def register_user(session: Session, user_create: UserCreate) -> User:
    email = str(user_create.email)
    if get_user_by_email(session, email) is not None:
        raise UserAlreadyExistsError("User email already exists")

    password_hash = hash_password(user_create.password.get_secret_value())
    return create_user(
        session,
        email=email,
        password_hash=password_hash,
        full_name=user_create.full_name,
        role="user",
        status="active",
    )


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(session, email)
    if user is None:
        return None

    if user.status != "active":
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
