"""Fase 4A: is_device_claimable — caso feliz y un test por condición que da False.

No conectado a ningún endpoint todavía; estos tests ejercitan la función
directamente sobre instancias de Device en memoria (no persistidas).
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.models import Device
from app.services.devices import PENDING_ACTIVATION, is_device_claimable


def _claimable_device(**overrides: object) -> Device:
    defaults: dict[str, object] = {
        "public_id": "PID-AAAAAAAAAA",
        "status": PENDING_ACTIVATION,
        "device_type": "qr_nfc_tag",
        "deleted_at": None,
        "user_id": None,
        "protected_person_id": None,
        "activated_at": None,
    }
    defaults.update(overrides)
    return Device(**defaults)


def test_is_device_claimable_happy_path() -> None:
    device = _claimable_device()

    assert is_device_claimable(device) is True


def test_is_device_claimable_false_when_deleted_at_set() -> None:
    device = _claimable_device(deleted_at=datetime.now(UTC))

    assert is_device_claimable(device) is False


def test_is_device_claimable_false_when_status_not_pending_activation() -> None:
    device = _claimable_device(status="active")

    assert is_device_claimable(device) is False


def test_is_device_claimable_false_when_user_id_set() -> None:
    device = _claimable_device(user_id=uuid4())

    assert is_device_claimable(device) is False


def test_is_device_claimable_false_when_protected_person_id_set() -> None:
    device = _claimable_device(protected_person_id=uuid4())

    assert is_device_claimable(device) is False


def test_is_device_claimable_false_when_activated_at_set() -> None:
    device = _claimable_device(activated_at=datetime.now(UTC))

    assert is_device_claimable(device) is False
