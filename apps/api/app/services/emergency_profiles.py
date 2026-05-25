"""Servicio de perfiles de emergencia."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Device, EmergencyProfile
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
    MEDICAL_DECISION_FIELD_PAIRS,
)
from app.services.profile_readiness import calculate_profile_readiness


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


def _build_create_profile_state(
    device_id: UUID, values: dict[str, object]
) -> EmergencyProfile:
    profile_values = PROFILE_CREATE_DEFAULTS | values
    return EmergencyProfile(device_id=device_id, **profile_values)


def _build_update_profile_state(
    profile: EmergencyProfile, values: dict[str, object]
) -> EmergencyProfile:
    profile_values = {
        field: values.get(field, getattr(profile, field))
        for field in PROFILE_PUBLICATION_FIELDS
    }
    return EmergencyProfile(device_id=profile.device_id, **profile_values)


def _validate_publication(device: Device, profile_state: EmergencyProfile) -> None:
    if not profile_state.is_public:
        return

    readiness = calculate_profile_readiness(device, profile_state)
    if not readiness.can_publish:
        raise EmergencyProfilePublicationError(PROFILE_PUBLICATION_ERROR_MESSAGE)


def create_or_update_profile_for_device(
    session: Session,
    *,
    device: Device,
    device_id: UUID,
    profile_data: EmergencyProfileCreate | EmergencyProfileUpdate,
) -> EmergencyProfile:
    values = profile_data.model_dump(exclude_unset=True)
    profile = get_profile_by_device_id(session, device_id)
    if profile is None:
        _validate_medical_decisions(_get_create_consistency_values(values))
        _validate_publication(device, _build_create_profile_state(device_id, values))
        return create_profile(session, device_id=device_id, **values)

    _validate_medical_decisions(_get_update_consistency_values(profile, values))
    _validate_publication(device, _build_update_profile_state(profile, values))
    return update_profile(session, profile, values)


def get_public_profile_by_public_id(
    session: Session, public_id: str
) -> EmergencyProfilePublicRead | None:
    profile = get_profile_by_public_id(session, public_id)
    if profile is None:
        return None

    return EmergencyProfilePublicRead.model_validate(profile)
