"""Endpoints protegidos de dispositivos."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies import CurrentUserDep, SessionDep, VerifiedEmailDep
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.core.settings import get_settings
from app.repositories.devices import get_device_by_public_id, get_devices_by_user_id
from app.schemas.device import DeviceActivate, DeviceCreate, DeviceRead
from app.services.claim_codes import verify_claim_code
from app.services.devices import create_pending_device

router = APIRouter(tags=["devices"])

MAX_CLAIM_ATTEMPTS = 5
CLAIM_LOCK_MINUTES = 15


@router.get("/api/devices", response_model=list[DeviceRead])
def list_devices(session: SessionDep, current_user: CurrentUserDep):
    return get_devices_by_user_id(session, current_user.id)


@router.post("/api/devices/activate", response_model=DeviceRead)
def activate_device(
    payload: DeviceActivate,
    session: SessionDep,
    current_user: VerifiedEmailDep,
    request: Request,
):
    settings = get_settings()
    client_ip = get_client_ip(request)
    public_id = payload.public_id.strip().upper()
    check_rate_limit(
        f"rl:devices:activate:ip:{client_ip}",
        settings.rate_limit_device_activate_ip_limit,
        settings.rate_limit_device_activate_ip_window_seconds,
    )
    check_rate_limit(
        f"rl:devices:activate:public_id:{public_id}",
        settings.rate_limit_device_activate_public_id_limit,
        settings.rate_limit_device_activate_public_id_window_seconds,
    )

    device = get_device_by_public_id(session, payload.public_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identifier not available",
        )

    if device.status != "pending_activation" or device.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identifier not available",
        )

    if device.claim_code_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier cannot be activated",
        )

    now = datetime.now(UTC)
    if device.claim_locked_until is not None and device.claim_locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many activation attempts. Try again later.",
        )

    if not verify_claim_code(payload.claim_code, device.claim_code_hash):
        device.claim_attempts = (device.claim_attempts or 0) + 1
        if device.claim_attempts >= MAX_CLAIM_ATTEMPTS:
            device.claim_locked_until = now + timedelta(minutes=CLAIM_LOCK_MINUTES)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation data",
        )

    device.user_id = current_user.id
    device.status = "active"
    device.activated_at = now
    device.claimed_at = now
    device.claim_attempts = 0
    device.claim_locked_until = None
    session.commit()
    session.refresh(device)
    return device


@router.post(
    "/api/admin/devices",
    response_model=DeviceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_device(
    session: SessionDep,
    current_user: VerifiedEmailDep,
    payload: DeviceCreate | None = None,
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return create_pending_device(session, label=payload.label if payload else None)
