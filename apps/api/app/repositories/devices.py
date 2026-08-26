"""Repositorio de dispositivos."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device


def get_device_by_id(session: Session, device_id: UUID) -> Device | None:
    statement = select(Device).where(
        Device.id == device_id, Device.deleted_at.is_(None)
    )
    return session.scalar(statement)


def get_device_by_public_id(session: Session, public_id: str) -> Device | None:
    statement = select(Device).where(
        Device.public_id == public_id, Device.deleted_at.is_(None)
    )
    return session.scalar(statement)


def get_devices_by_user_id(session: Session, user_id: UUID) -> list[Device]:
    statement = select(Device).where(
        Device.user_id == user_id, Device.deleted_at.is_(None)
    )
    return list(session.scalars(statement))


def get_device_by_id_including_deleted(session: Session, device_id: UUID) -> Device | None:
    return session.get(Device, device_id)


def get_device_by_public_id_including_deleted(session: Session, public_id: str) -> Device | None:
    statement = select(Device).where(Device.public_id == public_id)
    return session.scalar(statement)


def get_devices_by_user_id_including_deleted(session: Session, user_id: UUID) -> list[Device]:
    statement = select(Device).where(Device.user_id == user_id)
    return list(session.scalars(statement))


def create_device(
    session: Session,
    *,
    public_id: str,
    label: str | None = None,
    status: str = "pending_activation",
    device_type: str = "qr_nfc_tag",
) -> Device:
    device = Device(
        public_id=public_id,
        label=label,
        status=status,
        device_type=device_type,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def assign_device_to_user(session: Session, device: Device, user_id: UUID) -> Device:
    device.user_id = user_id
    device.status = "active"
    device.activated_at = datetime.now(UTC)
    session.commit()
    session.refresh(device)
    return device


def update_device_status(session: Session, device: Device, status: str) -> Device:
    device.status = status
    session.commit()
    session.refresh(device)
    return device
