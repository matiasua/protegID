"""Endpoints públicos de perfiles de emergencia."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import SessionDep
from app.schemas.emergency_profile import EmergencyProfilePublicRead
from app.services.emergency_profiles import get_public_profile_by_public_id

router = APIRouter(tags=["public-profiles"])


@router.get(
    "/api/public/profiles/{public_id}",
    response_model=EmergencyProfilePublicRead,
)
def get_public_emergency_profile(public_id: str, session: SessionDep):
    profile = get_public_profile_by_public_id(session, public_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public profile not found",
        )

    return profile
