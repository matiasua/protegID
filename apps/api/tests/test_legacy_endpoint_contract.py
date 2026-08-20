"""Bloque 4 — contract tests de los endpoints legacy device-scoped que el
frontend actual sigue usando:

    GET /api/devices/{device_id}/emergency-profile
    PUT /api/devices/{device_id}/emergency-profile
    GET /api/devices/{device_id}/emergency-profile/readiness

Verifican status codes, keys, tipos, y la coherencia predecible del adapter
legacy ante el caso documentado del switch de dominio:

    ProfileReadiness = READY  +  PublicAccessStatus = NOT OPERATIONAL

(perfil listo para publicar, pero el Device concreto no está operacional,
p. ej. status="lost"). El contrato legacy expone ambos hechos por separado
(`is_ready` vs. `is_public_operational`) en vez de colapsarlos en uno solo.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import Device
from tests.helpers import (
    create_pending_device_with_claim_code,
    public_ready_payload,
    ready_profile_payload,
)

READINESS_FIELDS_AND_TYPES = {
    "is_ready": bool,
    "can_publish": bool,
    "is_public_operational": bool,
    "public_profile_enabled": bool,
    "required_fields": list,
    "completed_fields": list,
    "missing_fields": list,
    "blocking_reasons": list,
    "consent_version": str,
}

PROFILE_READ_KEYS = {
    "id",
    "device_id",
    "display_name",
    "blood_type",
    "allergies",
    "medical_conditions",
    "medications",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relationship",
    "notes",
    "is_public",
    "medical_conditions_none",
    "allergies_none",
    "medications_none",
    "public_consent_accepted_at",
    "public_consent_version",
    "created_at",
    "updated_at",
    "deleted_at",
}


def _activate(client: TestClient, authed, device, claim_code: str) -> dict:
    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200
    return response.json()


def _assert_readiness_contract(body: dict) -> None:
    for field, expected_type in READINESS_FIELDS_AND_TYPES.items():
        assert field in body, f"missing field: {field}"
        assert isinstance(body[field], expected_type), (
            f"{field} expected {expected_type}, got {type(body[field])}"
        )
    assert "device_status" in body


# --- perfil incompleto + device active ---


def test_incomplete_profile_with_active_device(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json={"display_name": "Only a name"},
        cookies=authed.cookies,
        headers=authed.headers,
    )

    profile_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile", cookies=authed.cookies
    )
    assert profile_response.status_code == 200
    assert set(profile_response.json().keys()) == PROFILE_READ_KEYS

    readiness_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=authed.cookies,
    )
    assert readiness_response.status_code == 200
    body = readiness_response.json()
    _assert_readiness_contract(body)
    assert body["is_ready"] is False
    assert body["can_publish"] is False
    assert body["is_public_operational"] is False
    assert "emergency_contact_phone" in body["missing_fields"]
    assert body["device_status"] == "active"


# --- perfil ready/private + device active ---


def test_ready_private_profile_with_active_device(
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

    readiness_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=authed.cookies,
    )
    assert readiness_response.status_code == 200
    body = readiness_response.json()
    _assert_readiness_contract(body)
    assert body["is_ready"] is True
    assert body["missing_fields"] == []
    assert body["public_profile_enabled"] is False
    assert body["is_public_operational"] is False
    assert "profile_private" in body["blocking_reasons"]


# --- perfil ready/public + device active ---


def test_ready_public_profile_with_active_device(
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

    readiness_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=authed.cookies,
    )
    assert readiness_response.status_code == 200
    body = readiness_response.json()
    _assert_readiness_contract(body)
    assert body["is_ready"] is True
    assert body["can_publish"] is True
    assert body["public_profile_enabled"] is True
    assert body["is_public_operational"] is True
    assert body["blocking_reasons"] == []


# --- perfil ready/public + device lost: READY != OPERATIONAL, documentado ---


def test_ready_public_profile_with_lost_device_is_ready_but_not_operational(
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

    session = session_factory()
    try:
        db_device = session.get(Device, activated["id"])
        db_device.status = "lost"
        session.commit()
    finally:
        session.close()

    readiness_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=authed.cookies,
    )
    assert readiness_response.status_code == 200
    body = readiness_response.json()
    _assert_readiness_contract(body)

    # El punto central del contrato: ProfileReadiness sigue READY (es una
    # propiedad exclusiva del perfil), pero PublicAccessStatus para ESTE
    # device concreto ya no es operacional. El adapter legacy expone ambos
    # hechos sin colapsarlos.
    assert body["is_ready"] is True
    assert body["can_publish"] is True
    assert body["is_public_operational"] is False
    assert body["device_status"] == "lost"
    assert "device_not_active" in body["blocking_reasons"]


# --- consentimiento inválido ---


def test_invalid_consent_blocks_publication(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    """is_public=true con consentimiento inválido es rechazado en escritura
    (422, ver EmergencyProfilePublicationError): un perfil listo pero
    privado, con una versión de consentimiento desactualizada guardada, es lo
    que sí puede persistir — y debe seguir bloqueado para publicación."""
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    put_response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(public_consent_version="outdated-version"),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert put_response.status_code == 200

    rejected_publish = client.put(
        "/api/emergency-profile",
        json=public_ready_payload(public_consent_version="outdated-version"),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert rejected_publish.status_code == 422

    readiness_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=authed.cookies,
    )
    assert readiness_response.status_code == 200
    body = readiness_response.json()
    _assert_readiness_contract(body)
    assert body["is_ready"] is True
    assert body["can_publish"] is False
    assert body["public_profile_enabled"] is False
    assert body["is_public_operational"] is False
    assert "publication_not_eligible" in body["blocking_reasons"]
    assert "profile_private" in body["blocking_reasons"]


# --- device foreign user -> 404 ---


def test_foreign_user_gets_404_on_all_three_legacy_endpoints(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    owner = make_authed_user()
    intruder = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, owner, device, claim_code)

    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=owner.cookies,
        headers=owner.headers,
    )

    get_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile", cookies=intruder.cookies
    )
    put_response = client.put(
        f"/api/devices/{activated['id']}/emergency-profile",
        json=ready_profile_payload(),
        cookies=intruder.cookies,
        headers=intruder.headers,
    )
    readiness_response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=intruder.cookies,
    )

    assert get_response.status_code == 404
    assert put_response.status_code == 404
    assert readiness_response.status_code == 404
