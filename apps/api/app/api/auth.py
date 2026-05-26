"""Endpoints de autenticación."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.core.auth_cookies import clear_auth_session_cookie, set_auth_session_cookie
from app.core.csrf import clear_csrf_cookie, generate_csrf_token, set_csrf_cookie
from app.core.settings import get_settings
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserCreate, UserRead
from app.services.auth import UserAlreadyExistsError, authenticate_user, register_user
from app.services.auth_sessions import create_auth_session, revoke_auth_session_by_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserCreate, session: SessionDep):
    try:
        return register_user(session, payload)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User email already exists",
        ) from None


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    session: SessionDep,
    request: Request,
    response: Response,
) -> LoginResponse:
    user = authenticate_user(
        session,
        str(payload.email),
        payload.password.get_secret_value(),
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _, session_token = create_auth_session(
        session,
        user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_auth_session_cookie(
        response,
        session_token,
        max_age=get_settings().session_absolute_ttl_seconds,
    )
    set_csrf_cookie(response, generate_csrf_token())

    return LoginResponse(user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, session: SessionDep) -> None:
    session_token = request.cookies.get(get_settings().session_cookie_name)
    if session_token:
        revoke_auth_session_by_token(session, session_token)

    clear_auth_session_cookie(response)
    clear_csrf_cookie(response)


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUserDep):
    return current_user
