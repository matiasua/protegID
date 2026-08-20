"""Bloque 4: divergencia entre EmergencyProfile activos del mismo
ProtectedPerson (por corrupción/SQL manual) debe fallar cerrado, nunca
elegir ni reconciliar automáticamente."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import Device
from tests.helpers import (
    create_pending_device_with_claim_code,
    make_active_profile,
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


def _force_divergent_profiles(session_factory: sessionmaker, protected_person_id):
    session = session_factory()
    try:
        make_active_profile(
            session, protected_person_id=protected_person_id, display_name="Name A"
        )
        make_active_profile(
            session, protected_person_id=protected_person_id, display_name="Name B"
        )
    finally:
        session.close()


def test_public_endpoint_hides_profile_on_divergence(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    session = session_factory()
    try:
        protected_person_id = session.get(Device, activated["id"]).protected_person_id
    finally:
        session.close()

    _force_divergent_profiles(session_factory, protected_person_id)

    response = client.get(f"/api/public/profiles/{device.public_id}")

    assert response.status_code == 404


def test_private_account_endpoint_reports_integrity_conflict_on_divergence(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    session = session_factory()
    try:
        protected_person_id = session.get(Device, activated["id"]).protected_person_id
    finally:
        session.close()

    _force_divergent_profiles(session_factory, protected_person_id)

    response = client.get("/api/emergency-profile", cookies=authed.cookies)

    assert response.status_code == 409


def test_private_device_public_access_status_reports_integrity_conflict_on_divergence(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    session = session_factory()
    try:
        protected_person_id = session.get(Device, activated["id"]).protected_person_id
    finally:
        session.close()

    _force_divergent_profiles(session_factory, protected_person_id)

    response = client.get(
        f"/api/devices/{activated['id']}/public-access-status", cookies=authed.cookies
    )

    assert response.status_code == 409
