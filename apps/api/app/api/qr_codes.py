"""Endpoints admin de códigos QR de dispositivos."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.repositories.devices import get_device_by_id
from app.schemas.qr_code import DeviceQrMetadata, DeviceQrStatus
from app.services.qr_storage import (
    QR_CONTENT_TYPE,
    device_qr_exists,
    get_device_qr_object_key,
    upload_device_qr,
)

router = APIRouter(tags=["qr-codes"])


def _require_admin(current_user: CurrentUserDep) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


@router.post("/api/admin/devices/{device_id}/qr", response_model=DeviceQrMetadata)
def create_device_qr(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    _require_admin(current_user)

    device = get_device_by_id(session, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    object_key = upload_device_qr(device.public_id)
    return DeviceQrMetadata(
        device_id=device.id,
        public_id=device.public_id,
        object_key=object_key,
        content_type=QR_CONTENT_TYPE,
    )


@router.get("/api/admin/devices/{device_id}/qr", response_model=DeviceQrStatus)
def get_device_qr(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    _require_admin(current_user)

    device = get_device_by_id(session, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return DeviceQrStatus(
        device_id=device.id,
        public_id=device.public_id,
        object_key=get_device_qr_object_key(device.public_id),
        exists=device_qr_exists(device.public_id),
        content_type=QR_CONTENT_TYPE,
    )
