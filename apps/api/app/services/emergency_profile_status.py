"""Nuevo motor de estados del perfil de emergencia: readiness, publication eligibility y public access.

Estos tres dominios se mantienen deliberadamente separados:
- ProfileReadiness depende solo del EmergencyProfile.
- PublicationEligibility agrega el consentimiento (sigue sin depender de Device).
- PublicAccessStatus es el unico nivel que combina Device + ProtectedPerson + EmergencyProfile,
  y es especifico de un device/public_id concreto.

Bloque 2 (paralelo al flujo legacy): estas funciones todavia no gobiernan
ningun endpoint productivo. Ese recableo ocurre en un bloque posterior.
Ver app/services/profile_readiness.py para el motor legacy que sigue activo.
"""

from app.core.settings import get_settings
from app.models import Device, EmergencyProfile, ProtectedPerson
from app.schemas.emergency_profile import (
    ProfileReadinessRead,
    PublicAccessStatusRead,
    PublicationEligibilityRead,
)

REQUIRED_READINESS_FIELDS = (
    "display_name",
    "emergency_contact_name",
    "emergency_contact_phone",
    "medical_conditions_decision",
    "allergies_decision",
)


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _has_declared_or_none(value: str | None, none_declared: bool) -> bool:
    return _has_text(value) or none_declared


def calculate_profile_readiness(
    profile: EmergencyProfile | None,
) -> ProfileReadinessRead:
    completed_fields: list[str] = []

    if profile is not None:
        if _has_text(profile.display_name):
            completed_fields.append("display_name")
        if _has_text(profile.emergency_contact_name):
            completed_fields.append("emergency_contact_name")
        if _has_text(profile.emergency_contact_phone):
            completed_fields.append("emergency_contact_phone")
        if _has_declared_or_none(
            profile.medical_conditions, profile.medical_conditions_none
        ):
            completed_fields.append("medical_conditions_decision")
        if _has_declared_or_none(profile.allergies, profile.allergies_none):
            completed_fields.append("allergies_decision")

    missing_fields = [
        field for field in REQUIRED_READINESS_FIELDS if field not in completed_fields
    ]

    return ProfileReadinessRead(
        is_ready=not missing_fields,
        required_fields=list(REQUIRED_READINESS_FIELDS),
        completed_fields=completed_fields,
        missing_fields=missing_fields,
    )


def calculate_publication_eligibility(
    profile: EmergencyProfile | None,
) -> PublicationEligibilityRead:
    current_consent_version = get_settings().public_profile_consent_version
    readiness = calculate_profile_readiness(profile)

    consent_valid = bool(
        profile is not None
        and profile.public_consent_accepted_at is not None
        and profile.public_consent_version == current_consent_version
    )

    return PublicationEligibilityRead(
        profile_ready=readiness.is_ready,
        consent_valid=consent_valid,
        can_publish=readiness.is_ready and consent_valid,
        consent_version=current_consent_version,
    )


def calculate_public_access_status(
    device: Device | None,
    protected_person: ProtectedPerson | None,
    profile: EmergencyProfile | None,
) -> PublicAccessStatusRead:
    eligibility = calculate_publication_eligibility(profile)
    blocking_reasons: list[str] = []

    if device is None:
        blocking_reasons.append("device_missing")
    elif device.status != "active":
        blocking_reasons.append("device_not_active")
    elif device.deleted_at is not None:
        blocking_reasons.append("device_deleted")

    if protected_person is None:
        blocking_reasons.append("protected_person_missing")
    elif protected_person.deleted_at is not None:
        blocking_reasons.append("protected_person_deleted")

    if profile is None:
        blocking_reasons.append("profile_missing")
    else:
        if profile.deleted_at is not None:
            blocking_reasons.append("profile_deleted")
        if not profile.is_public:
            blocking_reasons.append("profile_private")

    if not eligibility.can_publish:
        blocking_reasons.append("publication_not_eligible")

    return PublicAccessStatusRead(
        is_operational=not blocking_reasons,
        device_status=device.status if device is not None else None,
        blocking_reasons=blocking_reasons,
    )
