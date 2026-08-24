"""Helpers compartidos para tests HTTP/DB de Bloque 4 (functional switch)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import Device, EmergencyProfile
from app.services.claim_codes import hash_claim_code
from app.services.device_ids import generate_public_id


def create_pending_device_with_claim_code(
    session: Session, *, claim_code: str = "AAAA-BBBB-CCCC"
) -> tuple[Device, str]:
    device = Device(
        public_id=generate_public_id(),
        status="pending_activation",
        device_type="qr_nfc_tag",
        claim_code_hash=hash_claim_code(claim_code),
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device, claim_code


def ready_profile_payload(**overrides: object) -> dict:
    payload = {
        "display_name": "Jane Doe",
        "emergency_contact_name": "John Doe",
        "emergency_contact_phone": "+54 9 11 5555-5555",
        "emergency_contact_relationship": "spouse",
        "medical_conditions_none": True,
        "allergies_none": True,
        "medications_none": True,
    }
    payload.update(overrides)
    return payload


def public_ready_payload(**overrides: object) -> dict:
    payload = ready_profile_payload(
        is_public=True,
        public_consent_accepted_at=datetime.now(UTC).isoformat(),
        public_consent_version=get_settings().public_profile_consent_version,
    )
    payload.update(overrides)
    return payload


def make_active_device_for_protected_person(
    session: Session, *, user_id, protected_person_id
) -> Device:
    device = Device(
        user_id=user_id,
        protected_person_id=protected_person_id,
        public_id=generate_public_id(),
        status="active",
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def make_active_profile(
    session: Session, *, protected_person_id, **overrides: object
) -> EmergencyProfile:
    values = ready_profile_payload()
    values.update(overrides)
    profile = EmergencyProfile(
        protected_person_id=protected_person_id,
        **values,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
