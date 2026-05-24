"""Endpoints protegidos de dispositivos."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.repositories.devices import get_device_by_public_id, get_devices_by_user_id
from app.schemas.device import DeviceActivate, DeviceCreate, DeviceRead
from app.services.claim_codes import verify_claim_code
from app.services.devices import create_pending_device

router = APIRouter(tags=["devices"])


@router.get("/api/devices", response_model=list[DeviceRead])
def list_devices(session: SessionDep, current_user: CurrentUserDep):
    return get_devices_by_user_id(session, current_user.id)


@router.post("/api/devices/activate", response_model=DeviceRead)
def activate_device(
    payload: DeviceActivate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
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

    if not verify_claim_code(payload.claim_code, device.claim_code_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation data",
        )

    now = datetime.now(UTC)
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
    current_user: CurrentUserDep,
    payload: DeviceCreate | None = None,
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return create_pending_device(session, label=payload.label if payload else None)
