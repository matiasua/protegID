"""Endpoints de perfiles de emergencia.

Account-scoped (fuente canónica, Bloque 4): /api/emergency-profile[...]
Device-scoped (DEPRECATED, mantenidos por compatibilidad con el frontend
actual): /api/devices/{device_id}/emergency-profile[...] — ver
app.services.emergency_profiles para el detalle de los adapters.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
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

logger = logging.getLogger("protegid-api.emergency_profiles")

# RFC 9745: Deprecation es un Structured Field cuyo valor debe ser una Date
# (`@<unix-timestamp>`), no el booleano `true`. Fecha en la que se declaró
# formalmente la deprecación de este contrato legacy (Bloque 8.1,
# 2026-08-22T00:00:00Z). Timestamp fijo, no dinámico: no debe recalcularse
# por request ni con datetime.now().
LEGACY_EMERGENCY_PROFILE_DEPRECATION = "@1787356800"


def mark_legacy_endpoint_use(
    response: Response, *, method: str, route: str, handler: str
) -> None:
    """Bloque 8.1: marca una respuesta de un endpoint device-scoped legacy de
    EmergencyProfile como deprecated (header + log), sin alterar body,
    status code ni autorización. No loguea PII ni contenido médico.

    Se debe invocar únicamente DESPUÉS de que el request superó ownership
    (ver `_get_owned_device`): "used" debe significar que un consumidor
    autorizado realmente llegó al contrato legacy, no cualquier intento.

    Decisión sobre `Link: rel="successor-version"` (RFC 8594): se omite
    deliberadamente. Esta API no está versionada (no hay /v2) y el
    successor semántico no es un mapeo 1:1 limpio: GET/PUT
    .../emergency-profile equivalen a /api/emergency-profile, pero
    .../emergency-profile/readiness combina ProfileReadiness +
    PublicationEligibility + PublicAccessStatus (específico de un device),
    mientras que /api/emergency-profile/status sólo expone readiness +
    publication_eligibility (sin PublicAccessStatus por device). Forzar el
    Link ahí sería impreciso. Se revisará si en el futuro se introduce un
    endpoint account-scoped que sí cubra ese dominio completo.

    Tampoco se agrega `Sunset` todavía: no hay fecha real de retiro."""
    response.headers["Deprecation"] = LEGACY_EMERGENCY_PROFILE_DEPRECATION
    logger.warning(
        "legacy_emergency_profile_endpoint_used",
        extra={"http_method": method, "route": route, "handler": handler},
    )


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
    deprecated=True,
)
def get_device_emergency_profile(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    response: Response,
):
    device = _get_owned_device(session, current_user, device_id)
    mark_legacy_endpoint_use(
        response,
        method="GET",
        route="/api/devices/{device_id}/emergency-profile",
        handler="get_device_emergency_profile",
    )
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
    deprecated=True,
)
def get_device_emergency_profile_readiness(
    device_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    response: Response,
):
    device = _get_owned_device(session, current_user, device_id)
    mark_legacy_endpoint_use(
        response,
        method="GET",
        route="/api/devices/{device_id}/emergency-profile/readiness",
        handler="get_device_emergency_profile_readiness",
    )
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
    deprecated=True,
)
def put_device_emergency_profile(
    device_id: UUID,
    payload: EmergencyProfileUpdate,
    session: SessionDep,
    current_user: VerifiedEmailDep,
    response: Response,
):
    device = _get_owned_device(session, current_user, device_id)
    mark_legacy_endpoint_use(
        response,
        method="PUT",
        route="/api/devices/{device_id}/emergency-profile",
        handler="put_device_emergency_profile",
    )
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
