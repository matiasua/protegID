"""Bloque 4: adapters device-scoped (DEPRECATED) delegan al perfil canónico."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from tests.helpers import create_pending_device_with_claim_code, ready_profile_payload


def _activate(client: TestClient, authed, device, claim_code: str) -> dict:
    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200
    return response.json()


def _two_activated_devices(client: TestClient, authed, session_factory: sessionmaker):
    session = session_factory()
    device_a, claim_a = create_pending_device_with_claim_code(session)
    device_b, claim_b = create_pending_device_with_claim_code(session)
    session.close()

    activated_a = _activate(client, authed, device_a, claim_a)
    activated_b = _activate(client, authed, device_b, claim_b)
    return activated_a, activated_b


def test_get_device_a_and_b_return_same_profile(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    device_a, device_b = _two_activated_devices(client, authed, session_factory)

    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response_a = client.get(
        f"/api/devices/{device_a['id']}/emergency-profile", cookies=authed.cookies
    )
    response_b = client.get(
        f"/api/devices/{device_b['id']}/emergency-profile", cookies=authed.cookies
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.json()["id"] == response_b.json()["id"]
    # el device_id devuelto refleja el device que preguntó, no el crudo de la fila
    assert response_a.json()["device_id"] == device_a["id"]
    assert response_b.json()["device_id"] == device_b["id"]


def test_put_via_device_b_updates_canonical_seen_by_device_a(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    device_a, device_b = _two_activated_devices(client, authed, session_factory)

    client.put(
        f"/api/devices/{device_b['id']}/emergency-profile",
        json=ready_profile_payload(display_name="Set via device B"),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response_a = client.get(
        f"/api/devices/{device_a['id']}/emergency-profile", cookies=authed.cookies
    )

    assert response_a.status_code == 200
    assert response_a.json()["display_name"] == "Set via device B"


def test_legacy_readiness_contract_preserved(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=authed.cookies,
    )

    assert response.status_code == 200
    body = response.json()
    for field in (
        "is_ready",
        "can_publish",
        "is_public_operational",
        "device_status",
        "public_profile_enabled",
        "required_fields",
        "completed_fields",
        "missing_fields",
        "blocking_reasons",
        "consent_version",
    ):
        assert field in body
    assert body["is_ready"] is True
    assert body["device_status"] == "active"
