"""Servicio de dispositivos."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Device, User
from app.repositories.devices import (
    create_device,
    get_device_by_id,
    get_device_by_public_id,
    update_device_status,
)
from app.services.device_ids import generate_public_id
from app.services.protected_persons import get_or_create_protected_person


PENDING_ACTIVATION = "pending_activation"
ACTIVE = "active"
DISABLED = "disabled"
LOST = "lost"
DEVICE_TYPE_QR_NFC_TAG = "qr_nfc_tag"
PUBLIC_ID_GENERATION_MAX_ATTEMPTS = 10


class DeviceNotFoundError(ValueError):
    pass


class DeviceActivationError(ValueError):
    pass


class PublicIdGenerationError(RuntimeError):
    pass


def generate_unique_public_id(session: Session) -> str:
    for _ in range(PUBLIC_ID_GENERATION_MAX_ATTEMPTS):
        public_id = generate_public_id()
        if get_device_by_public_id(session, public_id) is None:
            return public_id

    raise PublicIdGenerationError("Could not generate a unique device public_id")


def create_pending_device(session: Session, label: str | None = None) -> Device:
    public_id = generate_unique_public_id(session)
    return create_device(
        session,
        public_id=public_id,
        label=label,
        status=PENDING_ACTIVATION,
        device_type=DEVICE_TYPE_QR_NFC_TAG,
    )


def is_device_claimable(device: Device) -> bool:
    """True solo si el device puede ser reclamado vía POST /api/devices/activate.

    No conectado a ningún endpoint todavía (Fase 4A)."""
    return (
        device.deleted_at is None
        and device.status == PENDING_ACTIVATION
        and device.user_id is None
        and device.protected_person_id is None
        and device.activated_at is None
    )


def activate_device_for_user(session: Session, *, device: Device, user: User) -> Device:
    """Asocia un Device ya validado (public_id, claim code, lockout, status,
    ownership) al ProtectedPerson del usuario. El cliente nunca envía
    protected_person_id: la asociación es exclusivamente server-side.

    Un único commit al final evita estados parciales (ProtectedPerson creado
    pero Device no activado, o viceversa): get_or_create_protected_person se
    invoca con commit=False y comparte la misma transacción que la
    activación del Device."""
    protected_person = get_or_create_protected_person(session, user, commit=False)

    device.user_id = user.id
    device.protected_person_id = protected_person.id
    device.status = ACTIVE
    device.activated_at = datetime.now(UTC)
    session.commit()
    session.refresh(device)
    return device


def disable_device(session: Session, device_id: UUID) -> Device:
    device = get_device_by_id(session, device_id)
    if device is None:
        raise DeviceNotFoundError("Device not found")

    return update_device_status(session, device, DISABLED)


def mark_device_lost(session: Session, device_id: UUID) -> Device:
    device = get_device_by_id(session, device_id)
    if device is None:
        raise DeviceNotFoundError("Device not found")

    return update_device_status(session, device, LOST)
