"""Bloque 4: autorización/IDOR para los endpoints account-scoped y
device-scoped legacy adapters."""

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


def test_account_get_returns_only_current_user_profile(
    client: TestClient, make_authed_user
) -> None:
    user_a = make_authed_user()
    user_b = make_authed_user()

    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(display_name="A's profile"),
        cookies=user_a.cookies,
        headers=user_a.headers,
    )

    response = client.get("/api/emergency-profile", cookies=user_b.cookies)

    assert response.status_code == 404


def test_account_put_only_affects_current_user_profile(
    client: TestClient, make_authed_user
) -> None:
    user_a = make_authed_user()
    user_b = make_authed_user()

    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(display_name="A's profile"),
        cookies=user_a.cookies,
        headers=user_a.headers,
    )
    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(display_name="B's profile"),
        cookies=user_b.cookies,
        headers=user_b.headers,
    )

    response_a = client.get("/api/emergency-profile", cookies=user_a.cookies)
    response_b = client.get("/api/emergency-profile", cookies=user_b.cookies)

    assert response_a.json()["display_name"] == "A's profile"
    assert response_b.json()["display_name"] == "B's profile"


def test_user_cannot_use_legacy_endpoint_with_foreign_device(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    owner = make_authed_user()
    intruder = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, owner, device, claim_code)

    get_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile", cookies=intruder.cookies
    )
    put_response = client.put(
        f"/api/devices/{activated['id']}/emergency-profile",
        json=ready_profile_payload(),
        cookies=intruder.cookies,
        headers=intruder.headers,
    )

    assert get_response.status_code == 404
    assert put_response.status_code == 404


def test_client_cannot_send_protected_person_id_in_put_payload(
    client: TestClient, make_authed_user
) -> None:
    authed = make_authed_user()

    payload = ready_profile_payload()
    payload["protected_person_id"] = "11111111-1111-1111-1111-111111111111"

    response = client.put(
        "/api/emergency-profile",
        json=payload,
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 200
    assert "protected_person_id" not in response.json()


def test_client_cannot_activate_device_into_arbitrary_protected_person(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    """DeviceActivate solo acepta public_id + claim_code: no hay forma de
    que el cliente indique a qué ProtectedPerson debe asociarse el Device."""
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = client.post(
        "/api/devices/activate",
        json={
            "public_id": device.public_id,
            "claim_code": claim_code,
            "protected_person_id": "11111111-1111-1111-1111-111111111111",
        },
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == str(authed.user.id)


def test_public_endpoint_only_accepts_public_id_not_internal_ids(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    # Intentar usar el id interno del device en vez del public_id.
    response = client.get(f"/api/public/profiles/{activated['id']}")

    assert response.status_code == 404
