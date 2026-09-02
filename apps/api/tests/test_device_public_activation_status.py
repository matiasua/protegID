"""Fase 4B: GET /api/public/devices/{public_id}/activation-status usa
is_device_claimable() como única regla de disponibilidad.

Un Device encontrado pero no claimable debe seguir siendo externamente
indistinguible de un public_id inexistente: 404 con
detail="Identifier not available"."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import User
from app.services.device_ids import generate_public_id
from app.services.protected_persons import get_or_create_protected_person
from tests.helpers import create_pending_device_with_claim_code

EXPECTED_STATUS = 404
EXPECTED_BODY = {"detail": "Identifier not available"}


def _status(client: TestClient, public_id: str):
    return client.get(f"/api/public/devices/{public_id}/activation-status")


def test_claimable_device_returns_200(
    client: TestClient, session_factory: sessionmaker
) -> None:
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    public_id = device.public_id
    session.close()

    response = _status(client, public_id)

    assert response.status_code == 200
    assert response.json()["public_id"] == public_id


def test_nonexistent_public_id_returns_404(
    session_factory: sessionmaker, client: TestClient
) -> None:
    session = session_factory()
    try:
        public_id = generate_public_id()
    finally:
        session.close()

    response = _status(client, public_id)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_soft_deleted_device_returns_404(
    client: TestClient, session_factory: sessionmaker
) -> None:
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    device.deleted_at = datetime.now(UTC)
    session.add(device)
    session.commit()
    public_id = device.public_id
    session.close()

    response = _status(client, public_id)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_active_device_returns_404(
    client: TestClient, session_factory: sessionmaker
) -> None:
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    device.status = "active"
    session.add(device)
    session.commit()
    public_id = device.public_id
    session.close()

    response = _status(client, public_id)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_pending_with_user_id_assigned_returns_404(
    client: TestClient, session_factory: sessionmaker, make_authed_user
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    device.user_id = authed.user.id
    session.add(device)
    session.commit()
    public_id = device.public_id
    session.close()

    response = _status(client, public_id)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_pending_with_protected_person_id_assigned_returns_404(
    client: TestClient, session_factory: sessionmaker, make_authed_user
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    user = session.get(User, authed.user.id)
    protected_person = get_or_create_protected_person(session, user)
    device.protected_person_id = protected_person.id
    session.add(device)
    session.commit()
    public_id = device.public_id
    session.close()

    response = _status(client, public_id)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_pending_with_activated_at_set_returns_404(
    client: TestClient, session_factory: sessionmaker
) -> None:
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    device.activated_at = datetime.now(UTC)
    session.add(device)
    session.commit()
    public_id = device.public_id
    session.close()

    response = _status(client, public_id)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY
