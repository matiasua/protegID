"""Endpoints de perfiles de emergencia.

Contrato productivo, account-scoped (fuente canónica, Bloque 4):
/api/emergency-profile[...]. El contrato legacy device-scoped
(/api/devices/{device_id}/emergency-profile[...]) fue retirado en Bloque 8.3
tras confirmarse (Bloque 8.2) que nunca fue desplegado a producción/staging
ni tuvo consumidores externos al frontend actual, el cual ya usaba
exclusivamente el contrato account-scoped.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDep, SessionDep, VerifiedEmailDep
from app.schemas.emergency_profile import (
    EmergencyProfileRead,
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
    put_account_profile,
)
from app.services.protected_persons import ProtectedPersonSoftDeletedError

router = APIRouter(tags=["emergency-profiles"])


def _handle_write_errors(error: Exception):
    if isinstance(error, (EmergencyProfilePublicationError, ProfileConsistencyError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    raise error


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
