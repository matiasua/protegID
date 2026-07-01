"""Endpoints públicos de perfiles de emergencia."""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies import SessionDep
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.core.settings import get_settings
from app.schemas.emergency_profile import EmergencyProfilePublicRead
from app.services.emergency_profiles import get_public_profile_by_public_id

router = APIRouter(tags=["public-profiles"])


@router.get(
    "/api/public/profiles/{public_id}",
    response_model=EmergencyProfilePublicRead,
)
def get_public_emergency_profile(
    public_id: str,
    session: SessionDep,
    request: Request,
):
    settings = get_settings()
    client_ip = get_client_ip(request)
    normalized_public_id = public_id.strip().upper()
    check_rate_limit(
        f"rl:public:profile:ip:{client_ip}",
        settings.rate_limit_public_lookup_ip_limit,
        settings.rate_limit_public_lookup_ip_window_seconds,
    )
    check_rate_limit(
        f"rl:public:profile:public_id:{normalized_public_id}",
        settings.rate_limit_public_lookup_public_id_limit,
        settings.rate_limit_public_lookup_public_id_window_seconds,
    )

    profile = get_public_profile_by_public_id(session, public_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public profile not found",
        )

    return profile
