"""Fase 4D-A: get_qr_permissions — matriz de permisos QR por status,
precedencia absoluta de deleted_at, y fail-closed ante status desconocido.

Estos tests ejercitan la función directamente sobre instancias de Device
en memoria (no persistidas).
"""

from datetime import UTC, datetime

from app.models import Device
from app.services.devices import (
    ACTIVE,
    DISABLED,
    LOST,
    PENDING_ACTIVATION,
    QrPermissions,
    get_qr_permissions,
)


def _device(**overrides: object) -> Device:
    defaults: dict[str, object] = {
        "public_id": "PID-AAAAAAAAAA",
        "status": PENDING_ACTIVATION,
        "device_type": "qr_nfc_tag",
        "deleted_at": None,
    }
    defaults.update(overrides)
    return Device(**defaults)


def test_pending_activation_permissions() -> None:
    device = _device(status=PENDING_ACTIVATION)

    assert get_qr_permissions(device) == QrPermissions(
        can_create=True, can_get=True, can_download=True
    )


def test_active_permissions() -> None:
    device = _device(status=ACTIVE)

    assert get_qr_permissions(device) == QrPermissions(
        can_create=True, can_get=True, can_download=True
    )


def test_disabled_permissions() -> None:
    device = _device(status=DISABLED)

    assert get_qr_permissions(device) == QrPermissions(
        can_create=False, can_get=True, can_download=False
    )


def test_lost_permissions() -> None:
    device = _device(status=LOST)

    assert get_qr_permissions(device) == QrPermissions(
        can_create=False, can_get=True, can_download=False
    )


def test_unknown_status_fails_closed() -> None:
    device = _device(status="some_future_status")

    assert get_qr_permissions(device) == QrPermissions(
        can_create=False, can_get=False, can_download=False
    )


def test_deleted_at_overrides_pending_activation() -> None:
    device = _device(status=PENDING_ACTIVATION, deleted_at=datetime.now(UTC))

    assert get_qr_permissions(device) == QrPermissions(
        can_create=False, can_get=False, can_download=False
    )


def test_deleted_at_overrides_active() -> None:
    device = _device(status=ACTIVE, deleted_at=datetime.now(UTC))

    assert get_qr_permissions(device) == QrPermissions(
        can_create=False, can_get=False, can_download=False
    )


def test_deleted_at_overrides_disabled() -> None:
    device = _device(status=DISABLED, deleted_at=datetime.now(UTC))

    assert get_qr_permissions(device) == QrPermissions(
        can_create=False, can_get=False, can_download=False
    )


def test_deleted_at_overrides_lost() -> None:
    device = _device(status=LOST, deleted_at=datetime.now(UTC))

    assert get_qr_permissions(device) == QrPermissions(
        can_create=False, can_get=False, can_download=False
    )
