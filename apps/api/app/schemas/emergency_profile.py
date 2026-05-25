"""Schemas de perfil de emergencia."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


MEDICAL_DECISION_FIELD_PAIRS = (
    ("medical_conditions", "medical_conditions_none"),
    ("allergies", "allergies_none"),
    ("medications", "medications_none"),
)


def _has_text(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _validate_medical_decisions(profile_data: object) -> None:
    for text_field, none_field in MEDICAL_DECISION_FIELD_PAIRS:
        text_value = getattr(profile_data, text_field)
        none_value = getattr(profile_data, none_field)

        if none_value is True and _has_text(text_value):
            raise ValueError(
                f"{text_field} must be empty when {none_field} is true"
            )


class EmergencyProfileCreate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    blood_type: str | None = Field(default=None, max_length=10)
    allergies: str | None = None
    medical_conditions: str | None = None
    medications: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    emergency_contact_relationship: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    is_public: bool = False
    medical_conditions_none: bool = False
    allergies_none: bool = False
    medications_none: bool = False
    public_consent_accepted_at: datetime | None = None
    public_consent_version: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_medical_decisions(self):
        _validate_medical_decisions(self)
        return self


class EmergencyProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    blood_type: str | None = Field(default=None, max_length=10)
    allergies: str | None = None
    medical_conditions: str | None = None
    medications: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    emergency_contact_relationship: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    is_public: bool | None = None
    medical_conditions_none: bool | None = None
    allergies_none: bool | None = None
    medications_none: bool | None = None
    public_consent_accepted_at: datetime | None = None
    public_consent_version: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_medical_decisions(self):
        _validate_medical_decisions(self)
        return self


class EmergencyProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    display_name: str | None = None
    blood_type: str | None = None
    allergies: str | None = None
    medical_conditions: str | None = None
    medications: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None
    notes: str | None = None
    is_public: bool
    medical_conditions_none: bool
    allergies_none: bool
    medications_none: bool
    public_consent_accepted_at: datetime | None = None
    public_consent_version: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class EmergencyProfileReadinessRead(BaseModel):
    is_ready: bool
    can_publish: bool
    is_public_operational: bool
    device_status: str | None = None
    public_profile_enabled: bool
    required_fields: list[str]
    completed_fields: list[str]
    missing_fields: list[str]
    blocking_reasons: list[str]
    consent_version: str


class EmergencyProfilePublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str | None = None
    blood_type: str | None = None
    allergies: str | None = None
    medical_conditions: str | None = None
    medications: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None
    notes: str | None = None
