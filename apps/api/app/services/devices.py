"""Servicio de dispositivos."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Device
from app.repositories.devices import (
    assign_device_to_user,
    create_device,
    get_device_by_id,
    get_device_by_public_id,
    update_device_status,
)
from app.services.device_ids import generate_public_id


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


def activate_device_for_user(session: Session, *, public_id: str, user_id: UUID) -> Device:
    device = get_device_by_public_id(session, public_id)
    if device is None:
        raise DeviceNotFoundError("Device not found")

    if device.status != PENDING_ACTIVATION:
        raise DeviceActivationError("Device cannot be activated")

    return assign_device_to_user(session, device, user_id)


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
