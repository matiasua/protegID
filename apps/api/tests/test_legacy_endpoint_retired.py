"""Bloque 8.3 — retiro del contrato HTTP device-scoped legacy de
EmergencyProfile.

Bloque 8.2 confirmó (evidencia operacional externa al repo, no solo de
código) que este contrato nunca fue desplegado a producción/staging ni tuvo
consumidores externos al frontend actual, que ya usaba exclusivamente el
contrato account-scoped. Retirement fue aprobado sin ventana de observación.

Verifica:
- las 3 rutas legacy device-scoped desaparecen de OpenAPI;
- los requests a esas rutas ya no resuelven ningún handler (404 natural de
  ruta inexistente, no un 404 de negocio ni un tombstone implementado);
- el contrato productivo (account-scoped + PublicAccessStatus) permanece
  intacto en OpenAPI, sin `deprecated`.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from tests.helpers import create_pending_device_with_claim_code, ready_profile_payload

RETIRED_PATHS = {
    "/api/devices/{device_id}/emergency-profile",
    "/api/devices/{device_id}/emergency-profile/readiness",
}

PRODUCTIVE_PATHS = {
    "/api/emergency-profile": {"get", "put"},
    "/api/emergency-profile/status": {"get"},
    "/api/devices/{device_id}/public-access-status": {"get"},
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


# --- OpenAPI ---


def test_legacy_paths_are_absent_from_openapi(client: TestClient) -> None:
    spec = client.get("/api/openapi.json").json()
    paths = spec["paths"]

    for path in RETIRED_PATHS:
        assert path not in paths, f"retired path still in openapi: {path}"


def test_productive_paths_remain_in_openapi_without_deprecated(
    client: TestClient,
) -> None:
    spec = client.get("/api/openapi.json").json()
    paths = spec["paths"]

    for path, methods in PRODUCTIVE_PATHS.items():
        assert path in paths, f"missing productive path in openapi: {path}"
        for method in methods:
            operation = paths[path][method]
            assert operation.get("deprecated") is not True, (
                f"{method.upper()} {path} should not be deprecated"
            )


# --- Runtime 404 ---


def test_legacy_get_profile_route_no_longer_resolves(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()
    activated = _activate(client, authed, device, claim_code)

    response = client.get(
        f"/api/devices/{activated['id']}/emergency-profile", cookies=authed.cookies
    )
    assert response.status_code == 404


def test_legacy_put_profile_route_no_longer_resolves(
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
    assert response.status_code == 404


def test_legacy_readiness_route_no_longer_resolves(
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
    assert response.status_code == 404


def test_legacy_get_profile_route_404_even_without_auth(
    client: TestClient,
) -> None:
    """El 404 debe surgir del ruteo (ruta inexistente), no de una lógica de
    negocio/autorización. Debe ser el mismo 404 con o sin sesión."""
    response = client.get(
        "/api/devices/00000000-0000-0000-0000-000000000000/emergency-profile"
    )
    assert response.status_code == 404
