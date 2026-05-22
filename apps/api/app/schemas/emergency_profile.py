"""Schemas de perfil de emergencia."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    is_public: bool = True


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
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


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
