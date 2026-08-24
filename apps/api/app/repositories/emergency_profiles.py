"""Repositorio de perfiles de emergencia."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmergencyProfile


def get_active_profiles_by_protected_person_id(
    session: Session, protected_person_id: UUID
) -> list[EmergencyProfile]:
    """Perfiles activos (deleted_at IS NULL) de un ProtectedPerson. En una DB
    HEAD sana hay a lo sumo 1 (uq_emergency_profiles_active_protected_person);
    ver app.services.emergency_profile_canonical para la resolución/fail
    closed sobre este resultado."""
    statement = select(EmergencyProfile).where(
        EmergencyProfile.protected_person_id == protected_person_id,
        EmergencyProfile.deleted_at.is_(None),
    )
    return list(session.scalars(statement))


def create_profile(
    session: Session,
    *,
    protected_person_id: UUID | None = None,
    display_name: str | None = None,
    blood_type: str | None = None,
    allergies: str | None = None,
    medical_conditions: str | None = None,
    medications: str | None = None,
    emergency_contact_name: str | None = None,
    emergency_contact_phone: str | None = None,
    emergency_contact_relationship: str | None = None,
    notes: str | None = None,
    is_public: bool = False,
    medical_conditions_none: bool = False,
    allergies_none: bool = False,
    medications_none: bool = False,
    public_consent_accepted_at: datetime | None = None,
    public_consent_version: str | None = None,
) -> EmergencyProfile:
    profile = EmergencyProfile(
        protected_person_id=protected_person_id,
        display_name=display_name,
        blood_type=blood_type,
        allergies=allergies,
        medical_conditions=medical_conditions,
        medications=medications,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        emergency_contact_relationship=emergency_contact_relationship,
        notes=notes,
        is_public=is_public,
        medical_conditions_none=medical_conditions_none,
        allergies_none=allergies_none,
        medications_none=medications_none,
        public_consent_accepted_at=public_consent_accepted_at,
        public_consent_version=public_consent_version,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def update_profile(
    session: Session, profile: EmergencyProfile, values: dict[str, Any]
) -> EmergencyProfile:
    for field, value in values.items():
        setattr(profile, field, value)

    session.commit()
    session.refresh(profile)
    return profile


def apply_profile_values(profile: EmergencyProfile, values: dict[str, Any]) -> None:
    """Aplica `values` sobre `profile` en memoria, sin flush ni commit.

    Existe para que el caller pueda mutar varios EmergencyProfile (canonical +
    shadows) dentro de una misma transacción y hacer un único commit atómico
    al final. Ver app.services.emergency_profiles.put_account_profile.
    """
    for field, value in values.items():
        setattr(profile, field, value)
