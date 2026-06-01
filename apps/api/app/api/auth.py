"""Endpoints de autenticación."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.core.auth_cookies import clear_auth_session_cookie, set_auth_session_cookie
from app.core.csrf import clear_csrf_cookie, generate_csrf_token, set_csrf_cookie
from app.core.rate_limit import check_rate_limit, get_client_ip, hash_rate_limit_value
from app.core.settings import get_settings
from app.repositories.users import get_user_by_id
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterResponse,
    ResendVerificationResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.schemas.user import UserCreate, UserRead
from app.services.auth import (
    UserAlreadyExistsError,
    authenticate_user,
    register_user,
    send_user_email_verification,
    verify_user_email,
)
from app.services.auth_action_tokens import (
    PURPOSE_EMAIL_VERIFICATION,
    ActionTokenInvalidError,
    mark_action_token_used,
    revoke_pending_action_tokens,
    validate_action_token,
)
from app.services.auth_sessions import create_auth_session, revoke_auth_session_by_token
from app.services.email_delivery import EmailDeliveryError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _normalize_rate_limit_email(email: str) -> str:
    return email.strip().lower()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserCreate,
    session: SessionDep,
    request: Request,
) -> RegisterResponse:
    settings = get_settings()
    client_ip = get_client_ip(request)
    email_hash = hash_rate_limit_value(_normalize_rate_limit_email(str(payload.email)))
    check_rate_limit(
        f"rl:auth:register:ip:{client_ip}",
        settings.rate_limit_register_ip_limit,
        settings.rate_limit_register_ip_window_seconds,
    )
    check_rate_limit(
        f"rl:auth:register:email:{email_hash}",
        settings.rate_limit_register_email_limit,
        settings.rate_limit_register_email_window_seconds,
    )

    try:
        user = register_user(session, payload)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User email already exists",
        ) from None
    try:
        send_user_email_verification(session, user)
    except EmailDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email verification delivery failed",
        ) from None

    return RegisterResponse(
        user=UserRead.model_validate(user),
        verification_required=user.email_verified_at is None,
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
def verify_email(
    payload: VerifyEmailRequest,
    session: SessionDep,
    request: Request,
) -> VerifyEmailResponse:
    settings = get_settings()
    check_rate_limit(
        f"rl:auth:verify:ip:{get_client_ip(request)}",
        settings.rate_limit_verify_email_ip_limit,
        settings.rate_limit_verify_email_ip_window_seconds,
    )

    try:
        token_record = validate_action_token(
            session,
            payload.token,
            PURPOSE_EMAIL_VERIFICATION,
        )
    except ActionTokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        ) from None

    user = get_user_by_id(session, token_record.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    verify_user_email(session, user)
    mark_action_token_used(session, token_record)
    revoke_pending_action_tokens(session, user.id, PURPOSE_EMAIL_VERIFICATION)
    return VerifyEmailResponse(email_verified=True)


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
)
def resend_verification(
    current_user: CurrentUserDep,
    session: SessionDep,
    request: Request,
) -> ResendVerificationResponse:
    settings = get_settings()
    client_ip = get_client_ip(request)
    check_rate_limit(
        f"rl:auth:resend:ip:{client_ip}",
        settings.rate_limit_resend_verification_ip_limit,
        settings.rate_limit_resend_verification_ip_window_seconds,
    )
    check_rate_limit(
        f"rl:auth:resend:user:{current_user.id}",
        settings.rate_limit_resend_verification_user_limit,
        settings.rate_limit_resend_verification_user_window_seconds,
    )

    if current_user.email_verified_at is not None:
        return ResendVerificationResponse(
            verification_required=False,
            verification_sent=False,
        )

    try:
        send_user_email_verification(session, current_user)
    except EmailDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email verification delivery failed",
        ) from None

    return ResendVerificationResponse(
        verification_required=True,
        verification_sent=True,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    session: SessionDep,
    request: Request,
    response: Response,
) -> LoginResponse:
    settings = get_settings()
    client_ip = get_client_ip(request)
    email_hash = hash_rate_limit_value(_normalize_rate_limit_email(str(payload.email)))
    check_rate_limit(
        f"rl:auth:login:ip:{client_ip}",
        settings.rate_limit_login_ip_limit,
        settings.rate_limit_login_ip_window_seconds,
    )
    check_rate_limit(
        f"rl:auth:login:email:{email_hash}",
        settings.rate_limit_login_email_limit,
        settings.rate_limit_login_email_window_seconds,
    )

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
