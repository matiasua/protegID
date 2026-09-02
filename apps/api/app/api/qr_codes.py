"""Endpoints admin de códigos QR de dispositivos."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import CurrentUserDep, SessionDep, require_verified_email
from app.models import Device, User
from app.repositories.devices import get_device_by_id
from app.schemas.qr_code import DeviceQrMetadata, DeviceQrStatus
from app.services.devices import get_qr_permissions
from app.services.qr_storage import (
    QR_CONTENT_TYPE,
    device_qr_exists,
    download_device_qr,
    get_device_qr_object_key,
    upload_device_qr,
)

router = APIRouter(tags=["qr-codes"])

_QR_OPERATION_NOT_ALLOWED = "QR operation not allowed for device state"


def _require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    require_verified_email(current_user)


def _get_device_or_404(session: SessionDep, device_id: UUID) -> Device:
    device = get_device_by_id(session, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return device


@router.post("/api/admin/devices/{device_id}/qr", response_model=DeviceQrMetadata)
def create_device_qr(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    _require_admin(current_user)

    device = _get_device_or_404(session, device_id)
    if not get_qr_permissions(device).can_create:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_QR_OPERATION_NOT_ALLOWED,
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

    device = _get_device_or_404(session, device_id)
    if not get_qr_permissions(device).can_get:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_QR_OPERATION_NOT_ALLOWED,
        )

    return DeviceQrStatus(
        device_id=device.id,
        public_id=device.public_id,
        object_key=get_device_qr_object_key(device.public_id),
        exists=device_qr_exists(device.public_id),
        content_type=QR_CONTENT_TYPE,
    )


@router.get("/api/admin/devices/{device_id}/qr/download")
def download_device_qr_png(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    _require_admin(current_user)

    device = _get_device_or_404(session, device_id)
    if not get_qr_permissions(device).can_download:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_QR_OPERATION_NOT_ALLOWED,
        )

    try:
        png_bytes = download_device_qr(device.public_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code not found",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="QR code storage read failed",
        ) from None

    return Response(
        content=png_bytes,
        media_type=QR_CONTENT_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{device.public_id}.png"',
        },
    )
