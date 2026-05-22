"""Endpoints protegidos de dispositivos."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.repositories.devices import get_devices_by_user_id
from app.schemas.device import DeviceActivate, DeviceCreate, DeviceRead
from app.services.devices import (
    DeviceActivationError,
    DeviceNotFoundError,
    activate_device_for_user,
    create_pending_device,
)

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
    try:
        return activate_device_for_user(
            session,
            public_id=payload.public_id,
            user_id=current_user.id,
        )
    except DeviceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        ) from None
    except DeviceActivationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device cannot be activated",
        ) from None


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
