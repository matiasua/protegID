"""Endpoints protegidos de perfiles de emergencia."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUserDep, SessionDep
from app.models import Device, User
from app.repositories.devices import get_device_by_id
from app.repositories.emergency_profiles import get_profile_by_device_id
from app.schemas.emergency_profile import EmergencyProfileRead, EmergencyProfileUpdate
from app.services.emergency_profiles import (
    ProfileConsistencyError,
    create_or_update_profile_for_device,
)

router = APIRouter(tags=["emergency-profiles"])


def _get_owned_device(
    session: Session, current_user: User, device_id: UUID
) -> Device:
    device = get_device_by_id(session, device_id)
    if device is None or device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return device


@router.get(
    "/api/devices/{device_id}/emergency-profile",
    response_model=EmergencyProfileRead,
)
def get_device_emergency_profile(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    _get_owned_device(session, current_user, device_id)
    profile = get_profile_by_device_id(session, device_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency profile not found",
        )

    return profile


@router.put(
    "/api/devices/{device_id}/emergency-profile",
    response_model=EmergencyProfileRead,
)
def put_device_emergency_profile(
    device_id: UUID,
    payload: EmergencyProfileUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    _get_owned_device(session, current_user, device_id)
    try:
        return create_or_update_profile_for_device(
            session,
            device_id=device_id,
            profile_data=payload,
        )
    except ProfileConsistencyError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
