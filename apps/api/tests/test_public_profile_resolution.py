"""Bloque 4: switch real de resolución pública (public_id -> Device ->
protected_person_id -> ProtectedPerson -> perfil canónico)."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import Device, ProtectedPerson
from tests.helpers import (
    create_pending_device_with_claim_code,
    public_ready_payload,
    ready_profile_payload,
)


def _activate(client: TestClient, authed, device, claim_code: str) -> dict:
    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200
    return response.json()


def test_public_profile_available_when_ready_public_and_device_active(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json=public_ready_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response = client.get(f"/api/public/profiles/{device.public_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Jane Doe"
    assert "id" not in body
    assert "protected_person_id" not in body
    assert "device_id" not in body


def test_public_profile_unavailable_when_private(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response = client.get(f"/api/public/profiles/{device.public_id}")

    assert response.status_code == 404


def test_public_profile_unavailable_when_incomplete(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json={"display_name": "Incomplete only"},
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response = client.get(f"/api/public/profiles/{device.public_id}")

    assert response.status_code == 404


def test_public_profile_unavailable_with_outdated_consent(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json=public_ready_payload(public_consent_version="outdated-version"),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response = client.get(f"/api/public/profiles/{device.public_id}")

    assert response.status_code == 404


def test_lost_device_a_unavailable_but_active_device_b_serves_same_profile(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device_a, claim_a = create_pending_device_with_claim_code(session)
    device_b, claim_b = create_pending_device_with_claim_code(session)
    session.close()

    _activate(client, authed, device_a, claim_a)
    _activate(client, authed, device_b, claim_b)

    client.put(
        "/api/emergency-profile",
        json=public_ready_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    session = session_factory()
    try:
        db_device_a = session.get(Device, device_a.id)
        db_device_a.status = "lost"
        session.commit()
    finally:
        session.close()

    response_a = client.get(f"/api/public/profiles/{device_a.public_id}")
    response_b = client.get(f"/api/public/profiles/{device_b.public_id}")

    assert response_a.status_code == 404
    assert response_b.status_code == 200
    assert response_b.json()["display_name"] == "Jane Doe"

    # readiness a nivel de servicio sigue "ready": lo que cambia es el
    # access status por-device, no el perfil.
    status_response = client.get(
        "/api/emergency-profile/status", cookies=authed.cookies
    )
    assert status_response.json()["readiness"]["is_ready"] is True


def test_public_profile_unavailable_when_protected_person_soft_deleted(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json=public_ready_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    session = session_factory()
    try:
        protected_person = session.query(ProtectedPerson).filter_by(
            account_user_id=authed.user.id
        ).one()
        protected_person.deleted_at = datetime.now(UTC)
        session.commit()
    finally:
        session.close()

    response = client.get(f"/api/public/profiles/{device.public_id}")

    assert response.status_code == 404


def test_public_profile_not_found_for_unknown_public_id(client: TestClient) -> None:
    response = client.get("/api/public/profiles/PID-DOESNOTEXIST")

    assert response.status_code == 404
