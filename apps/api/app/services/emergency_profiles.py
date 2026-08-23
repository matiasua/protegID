"""Servicio de perfiles de emergencia — Bloque 4: switch a ProtectedPerson.

La fuente de verdad canónica es:
    User -> ProtectedPerson -> EmergencyProfile canónico (get_canonical_emergency_profile)

Los adapters *_legacy_device_* que soportaban el contrato HTTP device-scoped
fueron retirados en Bloque 8.3 (ver app.api.emergency_profiles). Este módulo
sigue exponiendo el contrato account-scoped y los helpers device-scoped que
permanecen productivos (get_public_access_status_for_device,
get_public_profile_by_public_id).
"""

import logging

from sqlalchemy.orm import Session

from app.models import Device, EmergencyProfile, ProtectedPerson, User
from app.repositories.devices import get_device_by_public_id
from app.repositories.emergency_profiles import apply_profile_values, create_profile
from app.repositories.protected_persons import get_by_id as get_protected_person_by_id
from app.schemas.emergency_profile import (
    EmergencyProfileCreate,
    EmergencyProfilePublicRead,
    EmergencyProfileUpdate,
    MEDICAL_DECISION_FIELD_PAIRS,
    PublicAccessStatusRead,
)
from app.services.emergency_profile_canonical import (
    CanonicalProfileDivergenceError,
    get_canonical_and_shadow_profiles_for_write,
    get_canonical_emergency_profile,
)
from app.services.emergency_profile_status import (
    calculate_publication_eligibility,
    calculate_public_access_status,
)
from app.services.protected_persons import (
    ProtectedPersonSoftDeletedError,
    get_or_create_protected_person,
    get_protected_person_for_user,
)

logger = logging.getLogger("protegid-api.emergency_profiles")


PROFILE_PUBLICATION_ERROR_MESSAGE = "Emergency profile is not ready for publication."

PROFILE_PUBLICATION_FIELDS = (
    "display_name",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relationship",
    "medical_conditions",
    "medical_conditions_none",
    "allergies",
    "allergies_none",
    "medications",
    "medications_none",
    "is_public",
    "public_consent_accepted_at",
    "public_consent_version",
    "deleted_at",
)

PROFILE_CREATE_DEFAULTS: dict[str, object] = {
    "display_name": None,
    "emergency_contact_name": None,
    "emergency_contact_phone": None,
    "emergency_contact_relationship": None,
    "medical_conditions": None,
    "medical_conditions_none": False,
    "allergies": None,
    "allergies_none": False,
    "medications": None,
    "medications_none": False,
    "is_public": False,
    "public_consent_accepted_at": None,
    "public_consent_version": None,
    "deleted_at": None,
}


class ProfileConsistencyError(ValueError):
    pass


class EmergencyProfilePublicationError(ValueError):
    pass


def _has_text(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _validate_medical_decisions(values: dict[str, object]) -> None:
    for text_field, none_field in MEDICAL_DECISION_FIELD_PAIRS:
        if values.get(none_field) is True and _has_text(values.get(text_field)):
            raise ProfileConsistencyError(
                f"{text_field} must be empty when {none_field} is true"
            )


def _get_create_consistency_values(values: dict[str, object]) -> dict[str, object]:
    consistency_values: dict[str, object] = {}

    for text_field, none_field in MEDICAL_DECISION_FIELD_PAIRS:
        consistency_values[text_field] = values.get(text_field)
        consistency_values[none_field] = values.get(none_field, False)

    return consistency_values


def _get_update_consistency_values(
    profile: EmergencyProfile, values: dict[str, object]
) -> dict[str, object]:
    consistency_values: dict[str, object] = {}

    for text_field, none_field in MEDICAL_DECISION_FIELD_PAIRS:
        consistency_values[text_field] = values.get(
            text_field, getattr(profile, text_field)
        )
        consistency_values[none_field] = values.get(
            none_field, getattr(profile, none_field)
        )

    return consistency_values


def _build_create_profile_state(values: dict[str, object]) -> EmergencyProfile:
    profile_values = PROFILE_CREATE_DEFAULTS | values
    return EmergencyProfile(**profile_values)


def _build_update_profile_state(
    profile: EmergencyProfile, values: dict[str, object]
) -> EmergencyProfile:
    profile_values = {
        field: values.get(field, getattr(profile, field))
        for field in PROFILE_PUBLICATION_FIELDS
    }
    return EmergencyProfile(**profile_values)


def _validate_publication(profile_state: EmergencyProfile) -> None:
    """Un update no puede dejar is_public=true sin PublicationEligibility.can_publish.

    Ya NO usa la legacy readiness.can_publish (que mezclaba Device): la
    publicación es exclusivamente una propiedad del perfil + consentimiento.
    """
    if not profile_state.is_public:
        return

    eligibility = calculate_publication_eligibility(profile_state)
    if not eligibility.can_publish:
        raise EmergencyProfilePublicationError(PROFILE_PUBLICATION_ERROR_MESSAGE)


def get_account_profile(session: Session, user: User) -> EmergencyProfile | None:
    """GET nunca crea. Ningún INSERT en este camino.

    None si el usuario no tiene ProtectedPerson, si el que tiene está
    soft-deleted, o si no tiene EmergencyProfile todavía. El caller (API)
    trata las tres situaciones de forma uniforme (recurso no disponible),
    salvo que decida diferenciar explícitamente.
    """
    try:
        protected_person = get_protected_person_for_user(session, user)
    except ProtectedPersonSoftDeletedError:
        return None

    if protected_person is None or protected_person.deleted_at is not None:
        return None

    return get_canonical_emergency_profile(session, protected_person)


def put_account_profile(
    session: Session,
    user: User,
    profile_data: EmergencyProfileCreate | EmergencyProfileUpdate,
) -> EmergencyProfile:
    """current_user -> get_or_create ProtectedPerson -> get_or_create perfil
    canónico -> actualizarlo. Un usuario sin Device puede crear su perfil:
    device_id queda NULL, protected_person_id siempre queda asignado.

    TRANSITIONAL — remove after EmergencyProfile.protected_person_id becomes
    UNIQUE. Mientras pueda haber más de un EmergencyProfile activo
    equivalente para el mismo ProtectedPerson (duplicados legacy por-Device),
    todo PUT debe: (1) resolver los activos, (2) comprobar que son
    equivalentes ANTES de escribir (fail closed si divergen), (3) aplicar la
    actualización al canonical, (4) propagar los mismos campos actualizados a
    los demás activos equivalentes (shadows), (5) un único commit atómico. Si
    cualquier parte de ese commit falla, ni el canonical ni los shadows
    quedan parcialmente modificados. No se hace merge médico, ni selección
    por "más reciente"/"más completo", ni reconciliación de divergentes: los
    shadows son solo espejos pasivos de esta ventana transitoria.
    """
    protected_person = get_or_create_protected_person(session, user)
    canonical, shadows = get_canonical_and_shadow_profiles_for_write(
        session, protected_person
    )

    values = profile_data.model_dump(exclude_unset=True)

    if canonical is None:
        _validate_medical_decisions(_get_create_consistency_values(values))
        _validate_publication(_build_create_profile_state(values))
        return create_profile(
            session,
            device_id=None,
            protected_person_id=protected_person.id,
            **values,
        )

    _validate_medical_decisions(_get_update_consistency_values(canonical, values))
    _validate_publication(_build_update_profile_state(canonical, values))

    apply_profile_values(canonical, values)
    for shadow in shadows:
        apply_profile_values(shadow, values)

    session.commit()
    session.refresh(canonical)
    return canonical


def get_account_profile_status(
    session: Session, user: User
) -> tuple[EmergencyProfile | None, bool]:
    """Para GET /api/emergency-profile/status. No crea nada.

    Devuelve (profile_or_none, protected_person_unavailable). El segundo
    valor distingue "no tiene ProtectedPerson todavía" (perfil incompleto,
    normal) de "tiene uno pero está soft-deleted" (no disponible, no es lo
    mismo que "incompleto").
    """
    try:
        protected_person = get_protected_person_for_user(session, user)
    except ProtectedPersonSoftDeletedError:
        return None, True

    if protected_person is None:
        return None, False

    if protected_person.deleted_at is not None:
        return None, True

    return get_canonical_emergency_profile(session, protected_person), False


def get_public_access_status_for_device(
    session: Session, device: Device
) -> PublicAccessStatusRead:
    """Para GET /api/devices/{device_id}/public-access-status (privado,
    dashboard). Deja que CanonicalProfileDivergenceError se propague: en un
    endpoint autenticado del dueño, una divergencia es un error de
    integridad que debe reportarse, no esconderse."""
    protected_person = None
    if device.protected_person_id is not None:
        protected_person = get_protected_person_by_id(session, device.protected_person_id)
        if protected_person is not None and protected_person.deleted_at is not None:
            protected_person = None

    profile = None
    if protected_person is not None:
        profile = get_canonical_emergency_profile(session, protected_person)

    return calculate_public_access_status(device, protected_person, profile)


def get_public_profile_by_public_id(
    session: Session, public_id: str
) -> EmergencyProfilePublicRead | None:
    """Switch real (Bloque 4): public_id -> Device -> Device.protected_person_id
    -> ProtectedPerson -> perfil canónico -> calculate_public_access_status.

    Fail closed ante divergencia: un visitante público nunca ve contenido
    médico de un perfil en estado de integridad indeterminado. Se loguea
    técnicamente (sin PII/contenido médico) y se responde igual que
    "no encontrado"."""
    device = get_device_by_public_id(session, public_id)
    if device is None:
        return None

    protected_person: ProtectedPerson | None = None
    if device.protected_person_id is not None:
        protected_person = get_protected_person_by_id(session, device.protected_person_id)
        if protected_person is not None and protected_person.deleted_at is not None:
            protected_person = None

    profile = None
    if protected_person is not None:
        try:
            profile = get_canonical_emergency_profile(session, protected_person)
        except CanonicalProfileDivergenceError as error:
            logger.error(
                "public_profile_canonical_divergence",
                extra={
                    "protected_person_id": str(error.protected_person_id),
                    "divergent_fields": error.divergent_fields,
                },
            )
            return None

    access = calculate_public_access_status(device, protected_person, profile)
    if not access.is_operational:
        return None

    return EmergencyProfilePublicRead.model_validate(profile)
