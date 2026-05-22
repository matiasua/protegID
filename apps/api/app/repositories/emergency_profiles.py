"""Repositorio de perfiles de emergencia."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, EmergencyProfile


def get_profile_by_device_id(
    session: Session, device_id: UUID
) -> EmergencyProfile | None:
    statement = select(EmergencyProfile).where(EmergencyProfile.device_id == device_id)
    return session.scalar(statement)


def get_profile_by_public_id(session: Session, public_id: str) -> EmergencyProfile | None:
    statement = (
        select(EmergencyProfile)
        .join(Device, EmergencyProfile.device_id == Device.id)
        .where(
            Device.public_id == public_id,
            Device.status == "active",
            EmergencyProfile.is_public.is_(True),
            EmergencyProfile.deleted_at.is_(None),
        )
    )
    return session.scalar(statement)


def create_profile(
    session: Session,
    *,
    device_id: UUID,
    display_name: str | None = None,
    blood_type: str | None = None,
    allergies: str | None = None,
    medical_conditions: str | None = None,
    medications: str | None = None,
    emergency_contact_name: str | None = None,
    emergency_contact_phone: str | None = None,
    emergency_contact_relationship: str | None = None,
    notes: str | None = None,
    is_public: bool = True,
) -> EmergencyProfile:
    profile = EmergencyProfile(
        device_id=device_id,
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
