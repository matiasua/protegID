"""Bloque 4: GET /api/devices/{device_id}/public-access-status (privado)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from tests.helpers import create_pending_device_with_claim_code, public_ready_payload


def _activate(client: TestClient, authed, device, claim_code: str) -> dict:
    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200
    return response.json()


def test_owner_can_read_public_access_status(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json=public_ready_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response = client.get(
        f"/api/devices/{activated['id']}/public-access-status", cookies=authed.cookies
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_operational"] is True
    assert "protected_person_id" not in body
    assert "profile_id" not in body


def test_foreign_user_cannot_read_public_access_status(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    owner = make_authed_user()
    other = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, owner, device, claim_code)

    response = client.get(
        f"/api/devices/{activated['id']}/public-access-status", cookies=other.cookies
    )

    assert response.status_code == 404


def test_unauthenticated_cannot_read_public_access_status(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    owner = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, owner, device, claim_code)

    response = client.get(f"/api/devices/{activated['id']}/public-access-status")

    assert response.status_code == 401
