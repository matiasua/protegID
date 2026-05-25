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
    MEDICAL_DECISION_FIELD_PAIRS,
)


class ProfileConsistencyError(ValueError):
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


def create_or_update_profile_for_device(
    session: Session,
    *,
    device_id: UUID,
    profile_data: EmergencyProfileCreate | EmergencyProfileUpdate,
) -> EmergencyProfile:
    values = profile_data.model_dump(exclude_unset=True)
    profile = get_profile_by_device_id(session, device_id)
    if profile is None:
        _validate_medical_decisions(_get_create_consistency_values(values))
        return create_profile(session, device_id=device_id, **values)

    _validate_medical_decisions(_get_update_consistency_values(profile, values))
    return update_profile(session, profile, values)


def get_public_profile_by_public_id(
    session: Session, public_id: str
) -> EmergencyProfilePublicRead | None:
    profile = get_profile_by_public_id(session, public_id)
    if profile is None:
        return None

    return EmergencyProfilePublicRead.model_validate(profile)
