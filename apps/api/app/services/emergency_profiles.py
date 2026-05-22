"""Servicio de perfiles de emergencia."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import EmergencyProfile
from app.repositories.emergency_profiles import (
    create_profile,
    get_profile_by_device_id,
    get_profile_by_public_id,
    update_profile,
)
from app.schemas.emergency_profile import (
    EmergencyProfileCreate,
    EmergencyProfilePublicRead,
    EmergencyProfileUpdate,
)


def create_or_update_profile_for_device(
    session: Session,
    *,
    device_id: UUID,
    profile_data: EmergencyProfileCreate | EmergencyProfileUpdate,
) -> EmergencyProfile:
    values = profile_data.model_dump(exclude_unset=True)
    profile = get_profile_by_device_id(session, device_id)
    if profile is None:
        return create_profile(session, device_id=device_id, **values)

    return update_profile(session, profile, values)


def get_public_profile_by_public_id(
    session: Session, public_id: str
) -> EmergencyProfilePublicRead | None:
    profile = get_profile_by_public_id(session, public_id)
    if profile is None:
        return None

    return EmergencyProfilePublicRead.model_validate(profile)
