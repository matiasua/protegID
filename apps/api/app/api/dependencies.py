"""Dependencias compartidas de la API."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.security import decode_access_token
from app.core.settings import get_settings
from app.models import User
from app.repositories.users import get_user_by_id
from app.services.auth_sessions import get_active_auth_session_by_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]
TokenDep = Annotated[str | None, Depends(oauth2_scheme)]


def get_current_user(request: Request, session: SessionDep, token: TokenDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    session_token = request.cookies.get(get_settings().session_cookie_name)
    if session_token:
        auth_session = get_active_auth_session_by_token(session, session_token)
        if auth_session is not None:
            user = get_user_by_id(session, auth_session.user_id)
            if user is None or user.status != "active":
                raise credentials_exception

            return user

    if token is None:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = UUID(str(subject))
    except (JWTError, ValueError):
        raise credentials_exception from None

    user = get_user_by_id(session, user_id)
    if user is None or user.status != "active":
        raise credentials_exception

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
