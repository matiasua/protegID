"""Endpoints públicos de dispositivos."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import SessionDep
from app.repositories.devices import get_device_by_public_id
from app.schemas.device import DeviceActivationStatusRead
from app.services.devices import PENDING_ACTIVATION


router = APIRouter(tags=["public-devices"])


@router.get(
    "/api/public/devices/{public_id}/activation-status",
    response_model=DeviceActivationStatusRead,
)
def get_public_device_activation_status(public_id: str, session: SessionDep):
    device = get_device_by_public_id(session, public_id)
    if device is None or device.status != PENDING_ACTIVATION:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identifier not available",
        )

    return DeviceActivationStatusRead(public_id=device.public_id)
