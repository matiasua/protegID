"""Endpoints de perfiles de emergencia.

Account-scoped (fuente canónica, Bloque 4): /api/emergency-profile[...]
Device-scoped (DEPRECATED, mantenidos por compatibilidad con el frontend
actual): /api/devices/{device_id}/emergency-profile[...] — ver
app.services.emergency_profiles para el detalle de los adapters.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUserDep, SessionDep, VerifiedEmailDep
from app.models import Device, User
from app.repositories.devices import get_device_by_id
from app.schemas.emergency_profile import (
    EmergencyProfileRead,
    EmergencyProfileReadinessRead,
    EmergencyProfileStatusRead,
    EmergencyProfileUpdate,
    ProfileReadinessRead,
    PublicationEligibilityRead,
)
from app.services.emergency_profile_canonical import CanonicalProfileDivergenceError
from app.services.emergency_profile_status import calculate_publication_eligibility
from app.services.emergency_profile_status import (
    calculate_profile_readiness as calculate_profile_readiness_v2,
)
from app.services.emergency_profiles import (
    EmergencyProfilePublicationError,
    ProfileConsistencyError,
    get_account_profile,
    get_account_profile_status,
    get_legacy_device_profile,
    get_legacy_readiness_for_device,
    put_account_profile,
    put_legacy_device_profile,
)
from app.services.protected_persons import ProtectedPersonSoftDeletedError

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


def _handle_write_errors(error: Exception):
    if isinstance(error, (EmergencyProfilePublicationError, ProfileConsistencyError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    raise error


def _to_read_with_device_id(
    profile, device_id: UUID | None
) -> EmergencyProfileRead:
    """Construye la respuesta legacy con el device_id de la request (no el
    device_id crudo de la fila), para que Device A y Device B devuelvan la
    misma ficha visible con el device_id correcto de quien preguntó."""
    read = EmergencyProfileRead.model_validate(profile)
    return read.model_copy(update={"device_id": device_id})


# --- Account-scoped (canónico) ---


@router.get(
    "/api/emergency-profile",
    response_model=EmergencyProfileRead,
)
def get_account_emergency_profile(
    session: SessionDep,
    current_user: CurrentUserDep,
):
    try:
        profile = get_account_profile(session, current_user)
    except CanonicalProfileDivergenceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emergency profile data integrity error",
        ) from error

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency profile not found",
        )

    return profile


@router.put(
    "/api/emergency-profile",
    response_model=EmergencyProfileRead,
)
def put_account_emergency_profile(
    payload: EmergencyProfileUpdate,
    session: SessionDep,
    current_user: VerifiedEmailDep,
):
    try:
        return put_account_profile(session, current_user, payload)
    except (EmergencyProfilePublicationError, ProfileConsistencyError) as error:
        _handle_write_errors(error)
    except CanonicalProfileDivergenceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emergency profile data integrity error",
        ) from error
    except ProtectedPersonSoftDeletedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Protected person is not available",
        ) from error


@router.get(
    "/api/emergency-profile/status",
    response_model=EmergencyProfileStatusRead,
)
def get_account_emergency_profile_status(
    session: SessionDep,
    current_user: CurrentUserDep,
):
    try:
        profile, unavailable = get_account_profile_status(session, current_user)
    except CanonicalProfileDivergenceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emergency profile data integrity error",
        ) from error

    if unavailable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency profile not found",
        )

    return EmergencyProfileStatusRead(
        readiness=ProfileReadinessRead.model_validate(
            calculate_profile_readiness_v2(profile)
        ),
        publication_eligibility=PublicationEligibilityRead.model_validate(
            calculate_publication_eligibility(profile)
        ),
    )


# --- Device-scoped (DEPRECATED adapters, compatibilidad con frontend actual) ---


@router.get(
    "/api/devices/{device_id}/emergency-profile",
    response_model=EmergencyProfileRead,
)
def get_device_emergency_profile(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    device = _get_owned_device(session, current_user, device_id)
    try:
        profile = get_legacy_device_profile(session, device)
    except CanonicalProfileDivergenceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emergency profile data integrity error",
        ) from error

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency profile not found",
        )

    return _to_read_with_device_id(profile, device.id)


@router.get(
    "/api/devices/{device_id}/emergency-profile/readiness",
    response_model=EmergencyProfileReadinessRead,
)
def get_device_emergency_profile_readiness(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    device = _get_owned_device(session, current_user, device_id)
    try:
        return get_legacy_readiness_for_device(session, device, current_user)
    except CanonicalProfileDivergenceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emergency profile data integrity error",
        ) from error


@router.put(
    "/api/devices/{device_id}/emergency-profile",
    response_model=EmergencyProfileRead,
)
def put_device_emergency_profile(
    device_id: UUID,
    payload: EmergencyProfileUpdate,
    session: SessionDep,
    current_user: VerifiedEmailDep,
):
    device = _get_owned_device(session, current_user, device_id)
    try:
        profile = put_legacy_device_profile(session, device, current_user, payload)
    except (EmergencyProfilePublicationError, ProfileConsistencyError) as error:
        _handle_write_errors(error)
        return
    except CanonicalProfileDivergenceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emergency profile data integrity error",
        ) from error
    except ProtectedPersonSoftDeletedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Protected person is not available",
        ) from error

    return _to_read_with_device_id(profile, device.id)
