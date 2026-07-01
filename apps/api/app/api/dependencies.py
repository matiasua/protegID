"""Dependencias compartidas de la API."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.settings import get_settings
from app.models import User
from app.repositories.users import get_user_by_id
from app.services.auth_sessions import get_active_auth_session_by_token

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(request: Request, session: SessionDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )

    session_token = request.cookies.get(get_settings().session_cookie_name)
    if not session_token:
        raise credentials_exception

    auth_session = get_active_auth_session_by_token(session, session_token)
    if auth_session is None:
        raise credentials_exception

    user = get_user_by_id(session, auth_session.user_id)
    if user is None or user.status != "active":
        raise credentials_exception

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_verified_email(current_user: User) -> User:
    if current_user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required.",
        )

    return current_user


def get_verified_email_user(current_user: CurrentUserDep) -> User:
    return require_verified_email(current_user)


VerifiedEmailDep = Annotated[User, Depends(get_verified_email_user)]
