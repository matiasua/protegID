"""Bloque 4: GET /api/devices/{device_id}/public-access-status (privado)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import Device
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


def test_ready_public_profile_with_lost_device_is_ready_but_not_operational(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    """Bloque 8.3: migrada desde el contrato legacy device-scoped readiness
    (retirado), que exponía is_ready y is_public_operational en la misma
    respuesta. El invariante documentado sigue siendo real y sigue siendo
    observable, ahora repartido entre los dos endpoints productivos que
    quedan: ProfileReadiness/PublicationEligibility son propiedades del
    perfil (GET /api/emergency-profile/status), mientras que
    PublicAccessStatus es específico de un device concreto
    (GET /api/devices/{device_id}/public-access-status). Un perfil puede
    estar completo y listo para publicar (READY) mientras el device
    concreto que lo sirve no está operacional (p. ej. status=lost)."""
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    put_response = client.put(
        "/api/emergency-profile",
        json=public_ready_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert put_response.status_code == 200

    status_response = client.get(
        "/api/emergency-profile/status", cookies=authed.cookies
    )
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["readiness"]["is_ready"] is True
    assert status_body["publication_eligibility"]["can_publish"] is True

    session = session_factory()
    try:
        db_device = session.get(Device, activated["id"])
        db_device.status = "lost"
        session.commit()
    finally:
        session.close()

    access_response = client.get(
        f"/api/devices/{activated['id']}/public-access-status",
        cookies=authed.cookies,
    )
    assert access_response.status_code == 200
    access_body = access_response.json()
    assert access_body["is_operational"] is False
    assert access_body["device_status"] == "lost"
    assert "device_not_active" in access_body["blocking_reasons"]
