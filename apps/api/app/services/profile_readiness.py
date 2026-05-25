"""Cálculo backend de readiness del perfil público."""

from app.core.settings import get_settings
from app.models import Device, EmergencyProfile
from app.schemas.emergency_profile import EmergencyProfileReadinessRead


REQUIRED_FIELDS = (
    "display_name",
    "emergency_contact_name",
    "emergency_contact_relationship",
    "emergency_contact_phone",
    "medical_conditions_decision",
    "allergies_decision",
    "medications_decision",
    "public_consent",
    "public_consent_version",
)

PROFILE_BLOCKING_REASONS = {
    "profile_missing",
    "profile_deleted",
    "consent_missing",
    "consent_version_outdated",
}


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _has_declared_or_none(value: str | None, none_declared: bool) -> bool:
    return _has_text(value) or none_declared


def calculate_profile_readiness(
    device: Device | None, profile: EmergencyProfile | None
) -> EmergencyProfileReadinessRead:
    current_consent_version = get_settings().public_profile_consent_version
    completed_fields: list[str] = []
    blocking_reasons: list[str] = []

    if device is None:
        blocking_reasons.append("device_missing")
        device_status = None
    else:
        device_status = device.status
        if device.status != "active":
            blocking_reasons.append("device_not_active")
        if device.deleted_at is not None:
            blocking_reasons.append("device_deleted")

    if profile is None:
        blocking_reasons.append("profile_missing")
        public_profile_enabled = False
    else:
        public_profile_enabled = profile.is_public
        if profile.deleted_at is not None:
            blocking_reasons.append("profile_deleted")

        if _has_text(profile.display_name):
            completed_fields.append("display_name")
        if _has_text(profile.emergency_contact_name):
            completed_fields.append("emergency_contact_name")
        if _has_text(profile.emergency_contact_relationship):
            completed_fields.append("emergency_contact_relationship")
        if _has_text(profile.emergency_contact_phone):
            completed_fields.append("emergency_contact_phone")
        if _has_declared_or_none(
            profile.medical_conditions, profile.medical_conditions_none
        ):
            completed_fields.append("medical_conditions_decision")
        if _has_declared_or_none(profile.allergies, profile.allergies_none):
            completed_fields.append("allergies_decision")
        if _has_declared_or_none(profile.medications, profile.medications_none):
            completed_fields.append("medications_decision")

        if profile.public_consent_accepted_at is None:
            blocking_reasons.append("consent_missing")
        else:
            completed_fields.append("public_consent")

        if profile.public_consent_version == current_consent_version:
            completed_fields.append("public_consent_version")
        else:
            blocking_reasons.append("consent_version_outdated")

    missing_fields = [
        field for field in REQUIRED_FIELDS if field not in completed_fields
    ]
    has_profile_blocking_reasons = any(
        reason in PROFILE_BLOCKING_REASONS for reason in blocking_reasons
    )
    is_ready = not missing_fields and not has_profile_blocking_reasons
    can_publish = (
        is_ready
        and device is not None
        and device.status == "active"
        and device.deleted_at is None
        and profile is not None
        and profile.deleted_at is None
    )

    return EmergencyProfileReadinessRead(
        is_ready=is_ready,
        can_publish=can_publish,
        is_public_operational=can_publish and public_profile_enabled,
        device_status=device_status,
        public_profile_enabled=public_profile_enabled,
        required_fields=list(REQUIRED_FIELDS),
        completed_fields=completed_fields,
        missing_fields=missing_fields,
        blocking_reasons=blocking_reasons,
        consent_version=current_consent_version,
    )
