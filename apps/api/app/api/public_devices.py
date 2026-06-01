"""Endpoints públicos de dispositivos."""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies import SessionDep
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.core.settings import get_settings
from app.repositories.devices import get_device_by_public_id
from app.schemas.device import DeviceActivationStatusRead
from app.services.devices import PENDING_ACTIVATION


router = APIRouter(tags=["public-devices"])


@router.get(
    "/api/public/devices/{public_id}/activation-status",
    response_model=DeviceActivationStatusRead,
)
def get_public_device_activation_status(
    public_id: str,
    session: SessionDep,
    request: Request,
):
    settings = get_settings()
    client_ip = get_client_ip(request)
    normalized_public_id = public_id.strip().upper()
    check_rate_limit(
        f"rl:public:activation-status:ip:{client_ip}",
        settings.rate_limit_public_lookup_ip_limit,
        settings.rate_limit_public_lookup_ip_window_seconds,
    )
    check_rate_limit(
        f"rl:public:activation-status:public_id:{normalized_public_id}",
        settings.rate_limit_public_lookup_public_id_limit,
        settings.rate_limit_public_lookup_public_id_window_seconds,
    )

    device = get_device_by_public_id(session, public_id)
    if device is None or device.status != PENDING_ACTIVATION:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identifier not available",
        )

    return DeviceActivationStatusRead(public_id=device.public_id)
