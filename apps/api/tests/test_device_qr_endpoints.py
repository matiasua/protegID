"""Fase 4D-B: wiring de get_qr_permissions() a los 3 endpoints admin de QR.

Cubre semántica HTTP (404 para device inexistente/soft-deleted, 409 para
estados bloqueados por la matriz de permisos) y verifica que un estado
bloqueado no llegue a tocar storage. La matriz de permisos en sí ya está
cubierta en test_device_qr_permissions.py; estos tests no la duplican.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.core.settings import get_settings
from app.models import Device
from app.repositories.users import create_user, mark_user_email_verified
from app.services.auth_sessions import create_auth_session
from app.services.device_ids import generate_public_id
from tests.conftest import AuthedUser


def _make_admin_user(session_factory: sessionmaker) -> AuthedUser:
    session = session_factory()
    try:
        user = create_user(
            session,
            email=f"{uuid4().hex}@example.com",
            password_hash=hash_password("Sup3rSecret!1"),
            role="admin",
        )
        mark_user_email_verified(session, user)
        _, session_token = create_auth_session(session, user.id)
    finally:
        session.close()

    settings = get_settings()
    csrf_token = f"csrf-{uuid4().hex}"
    cookies = {
        settings.session_cookie_name: session_token,
        settings.csrf_cookie_name: csrf_token,
    }
    headers = {settings.csrf_header_name: csrf_token}
    return AuthedUser(user=user, cookies=cookies, headers=headers)


def _make_device(session_factory: sessionmaker, **overrides: object) -> Device:
    defaults: dict[str, object] = {
        "public_id": generate_public_id(),
        "status": "pending_activation",
        "device_type": "qr_nfc_tag",
        "deleted_at": None,
    }
    defaults.update(overrides)

    session = session_factory()
    try:
        device = Device(**defaults)
        session.add(device)
        session.commit()
        session.refresh(device)
        return device
    finally:
        session.close()


@pytest.fixture
def admin(session_factory: sessionmaker) -> AuthedUser:
    return _make_admin_user(session_factory)


@pytest.fixture(autouse=True)
def _mock_qr_storage(monkeypatch: pytest.MonkeyPatch):
    """Reemplaza los 3 puntos de contacto con storage en app.api.qr_codes.
    autouse para que ningún test de este archivo golpee S3/MinIO real, y
    para poder aseverar en los tests bloqueados que no fueron invocados."""
    upload_calls: list[str] = []
    exists_calls: list[str] = []
    download_calls: list[str] = []

    def _fake_upload(public_id: str) -> str:
        upload_calls.append(public_id)
        return f"qr/devices/{public_id}.png"

    def _fake_exists(public_id: str) -> bool:
        exists_calls.append(public_id)
        return True

    def _fake_download(public_id: str) -> bytes:
        download_calls.append(public_id)
        return b"fake-png-bytes"

    def _fake_object_key(public_id: str) -> str:
        return f"qr/devices/{public_id}.png"

    monkeypatch.setattr("app.api.qr_codes.upload_device_qr", _fake_upload)
    monkeypatch.setattr("app.api.qr_codes.device_qr_exists", _fake_exists)
    monkeypatch.setattr("app.api.qr_codes.download_device_qr", _fake_download)
    monkeypatch.setattr("app.api.qr_codes.get_device_qr_object_key", _fake_object_key)

    return {
        "upload": upload_calls,
        "exists": exists_calls,
        "download": download_calls,
    }


def _create(client: TestClient, admin: AuthedUser, device: Device):
    return client.post(
        f"/api/admin/devices/{device.id}/qr",
        cookies=admin.cookies,
        headers=admin.headers,
    )


def _get(client: TestClient, admin: AuthedUser, device: Device):
    return client.get(
        f"/api/admin/devices/{device.id}/qr",
        cookies=admin.cookies,
        headers=admin.headers,
    )


def _download(client: TestClient, admin: AuthedUser, device: Device):
    return client.get(
        f"/api/admin/devices/{device.id}/qr/download",
        cookies=admin.cookies,
        headers=admin.headers,
    )


@pytest.mark.parametrize("status_value", ["pending_activation", "active"])
def test_allowed_status_permits_create_get_download(
    client: TestClient,
    admin: AuthedUser,
    session_factory: sessionmaker,
    _mock_qr_storage,
    status_value: str,
) -> None:
    device = _make_device(session_factory, status=status_value)

    create_response = _create(client, admin, device)
    get_response = _get(client, admin, device)
    download_response = _download(client, admin, device)

    assert create_response.status_code == 200
    assert get_response.status_code == 200
    assert download_response.status_code == 200
    assert _mock_qr_storage["upload"] == [device.public_id]
    assert _mock_qr_storage["exists"] == [device.public_id]
    assert _mock_qr_storage["download"] == [device.public_id]


@pytest.mark.parametrize("status_value", ["disabled", "lost"])
def test_readonly_status_blocks_create_and_download_but_allows_get(
    client: TestClient,
    admin: AuthedUser,
    session_factory: sessionmaker,
    _mock_qr_storage,
    status_value: str,
) -> None:
    device = _make_device(session_factory, status=status_value)

    create_response = _create(client, admin, device)
    get_response = _get(client, admin, device)
    download_response = _download(client, admin, device)

    assert create_response.status_code == 409
    assert create_response.json()["detail"] == "QR operation not allowed for device state"
    assert download_response.status_code == 409
    assert download_response.json()["detail"] == "QR operation not allowed for device state"
    assert get_response.status_code == 200

    assert _mock_qr_storage["upload"] == []
    assert _mock_qr_storage["download"] == []
    assert _mock_qr_storage["exists"] == [device.public_id]


def test_soft_deleted_device_is_404_for_all_three_operations(
    client: TestClient,
    admin: AuthedUser,
    session_factory: sessionmaker,
    _mock_qr_storage,
) -> None:
    from datetime import UTC, datetime

    device = _make_device(session_factory, status="active", deleted_at=datetime.now(UTC))

    create_response = _create(client, admin, device)
    get_response = _get(client, admin, device)
    download_response = _download(client, admin, device)

    assert create_response.status_code == 404
    assert get_response.status_code == 404
    assert download_response.status_code == 404
    assert create_response.json()["detail"] == "Device not found"
    assert get_response.json()["detail"] == "Device not found"
    assert download_response.json()["detail"] == "Device not found"

    assert _mock_qr_storage["upload"] == []
    assert _mock_qr_storage["exists"] == []
    assert _mock_qr_storage["download"] == []


def test_nonexistent_device_is_404_for_all_three_operations(
    client: TestClient,
    admin: AuthedUser,
    _mock_qr_storage,
) -> None:
    missing_device = Device(id=uuid4(), public_id="MISSING-000000", status="active")

    create_response = _create(client, admin, missing_device)
    get_response = _get(client, admin, missing_device)
    download_response = _download(client, admin, missing_device)

    assert create_response.status_code == 404
    assert get_response.status_code == 404
    assert download_response.status_code == 404

    assert _mock_qr_storage["upload"] == []
    assert _mock_qr_storage["exists"] == []
    assert _mock_qr_storage["download"] == []


def test_unknown_status_blocks_all_three_operations_fail_closed(
    client: TestClient,
    admin: AuthedUser,
    session_factory: sessionmaker,
    _mock_qr_storage,
) -> None:
    device = _make_device(session_factory, status="quarantined")

    create_response = _create(client, admin, device)
    get_response = _get(client, admin, device)
    download_response = _download(client, admin, device)

    assert create_response.status_code == 409
    assert get_response.status_code == 409
    assert download_response.status_code == 409

    assert _mock_qr_storage["upload"] == []
    assert _mock_qr_storage["exists"] == []
    assert _mock_qr_storage["download"] == []
