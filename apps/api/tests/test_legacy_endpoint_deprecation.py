"""Bloque 8.1 — deprecation & observability de los endpoints device-scoped
legacy de EmergencyProfile.

Verifica:
- header `Deprecation: @1787356800` (RFC 9745) en las 3 rutas legacy;
- OpenAPI marca `deprecated: true` en esas 3 rutas y NO en las account-scoped
  ni en `/api/devices/{device_id}/public-access-status`;
- el logging de uso legacy emite el evento solo cuando el request superó
  ownership (no en rechazos de autorización), sin filtrar PII/contenido
  médico.
"""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.emergency_profiles import LEGACY_EMERGENCY_PROFILE_DEPRECATION
from tests.helpers import create_pending_device_with_claim_code, ready_profile_payload

LEGACY_PATHS = {
    "/api/devices/{device_id}/emergency-profile": {"get", "put"},
    "/api/devices/{device_id}/emergency-profile/readiness": {"get"},
}

NON_DEPRECATED_PATHS = {
    "/api/emergency-profile": {"get", "put"},
    "/api/emergency-profile/status": {"get"},
    "/api/devices/{device_id}/public-access-status": {"get"},
}


@pytest.fixture
def legacy_logger_enabled():
    """Alembic's env.py calls logging.config.fileConfig(...) with the
    default disable_existing_loggers=True. Tests that run alembic commands
    in-process (test_db_at_revision_fixtures.py, test_protected_person_*.py)
    can leave this module's logger disabled for the rest of the suite.
    Re-enable it explicitly so caplog-based tests don't depend on run
    order."""
    logger = logging.getLogger("protegid-api.emergency_profiles")
    logger.disabled = False
    yield logger


def _activate(client: TestClient, authed, device, claim_code: str) -> dict:
    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200
    return response.json()


# --- OpenAPI ---


def test_legacy_paths_are_marked_deprecated_in_openapi(client: TestClient) -> None:
    spec = client.get("/api/openapi.json").json()
    paths = spec["paths"]

    for path, methods in LEGACY_PATHS.items():
        assert path in paths, f"missing path in openapi: {path}"
        for method in methods:
            operation = paths[path][method]
            assert operation.get("deprecated") is True, (
                f"{method.upper()} {path} should be deprecated"
            )


def test_account_scoped_and_public_access_status_are_not_deprecated(
    client: TestClient,
) -> None:
    spec = client.get("/api/openapi.json").json()
    paths = spec["paths"]

    for path, methods in NON_DEPRECATED_PATHS.items():
        assert path in paths, f"missing path in openapi: {path}"
        for method in methods:
            operation = paths[path][method]
            assert operation.get("deprecated") is not True, (
                f"{method.upper()} {path} should NOT be deprecated"
            )


# --- Headers ---


def test_legacy_get_profile_returns_deprecation_header(
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
        f"/api/devices/{activated['id']}/emergency-profile", cookies=authed.cookies
    )
    assert response.status_code == 200
    assert response.headers["deprecation"] == LEGACY_EMERGENCY_PROFILE_DEPRECATION


def test_legacy_put_profile_returns_deprecation_header(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    response = client.put(
        f"/api/devices/{activated['id']}/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200
    assert response.headers["deprecation"] == LEGACY_EMERGENCY_PROFILE_DEPRECATION


def test_legacy_readiness_returns_deprecation_header(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile/readiness",
        cookies=authed.cookies,
    )
    assert response.status_code == 200
    assert response.headers["deprecation"] == LEGACY_EMERGENCY_PROFILE_DEPRECATION


def test_public_access_status_has_no_deprecation_header(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    response = client.get(
        f"/api/devices/{activated['id']}/public-access-status",
        cookies=authed.cookies,
    )
    assert response.status_code == 200
    assert "deprecation" not in response.headers


def test_account_scoped_endpoints_have_no_deprecation_header(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    _activate(client, authed, device, claim_code)

    put_response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert "deprecation" not in put_response.headers

    get_response = client.get("/api/emergency-profile", cookies=authed.cookies)
    assert "deprecation" not in get_response.headers

    status_response = client.get(
        "/api/emergency-profile/status", cookies=authed.cookies
    )
    assert "deprecation" not in status_response.headers


# --- Logging ---


def test_legacy_endpoint_use_emits_warning_without_pii(
    client: TestClient,
    make_authed_user,
    session_factory: sessionmaker,
    legacy_logger_enabled,
    caplog,
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    put_response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(
            medical_conditions="Diabetes tipo 2",
            medical_conditions_none=False,
            emergency_contact_phone="+54 9 11 4444-4444",
        ),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert put_response.status_code == 200

    with caplog.at_level(
        logging.WARNING, logger="protegid-api.emergency_profiles"
    ):
        response = client.get(
            f"/api/devices/{activated['id']}/emergency-profile",
            cookies=authed.cookies,
        )
    assert response.status_code == 200

    legacy_records = [
        record
        for record in caplog.records
        if record.message == "legacy_emergency_profile_endpoint_used"
    ]
    assert len(legacy_records) == 1
    record = legacy_records[0]
    assert record.levelname == "WARNING"
    assert record.route == "/api/devices/{device_id}/emergency-profile"
    assert record.http_method == "GET"
    assert record.handler == "get_device_emergency_profile"

    rendered = caplog.text
    assert "Diabetes" not in rendered
    assert "4444-4444" not in rendered
    assert claim_code not in rendered
    assert str(device.public_id) not in rendered


def test_foreign_user_ownership_rejection_does_not_emit_legacy_used(
    client: TestClient,
    make_authed_user,
    session_factory: sessionmaker,
    legacy_logger_enabled,
    caplog,
) -> None:
    """'used' debe significar que un consumidor autorizado llegó al
    contrato legacy. Un intento de un usuario ajeno al Device debe seguir
    respondiendo 404 (sin cambios de autorización), pero NO debe contar
    como uso legítimo para el retirement gate de Bloque 8.2."""
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

    with caplog.at_level(
        logging.WARNING, logger="protegid-api.emergency_profiles"
    ):
        get_response = client.get(
            f"/api/devices/{activated['id']}/emergency-profile",
            cookies=intruder.cookies,
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
    assert "deprecation" not in get_response.headers
    assert "deprecation" not in put_response.headers
    assert "deprecation" not in readiness_response.headers

    legacy_records = [
        record
        for record in caplog.records
        if record.message == "legacy_emergency_profile_endpoint_used"
    ]
    assert legacy_records == []
