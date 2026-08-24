"""D2: la activación de Device no debe permitir enumerar public_id/estado
mediante diferencias de status code o body HTTP.

Todas las condiciones de credencial/estado inválidas (public_id inexistente,
Device no pending, Device ya asignado, claim_code_hash ausente, claim code
incorrecto) deben producir exactamente la misma respuesta externa: 400 con
detail="Invalid activation data". Los side effects internos (mutaciones DB)
deben seguir diferenciados según corresponda."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings
from app.models import Device
from app.services.claim_codes import hash_claim_code
from tests.helpers import create_pending_device_with_claim_code
from app.services.device_ids import generate_public_id

EXPECTED_STATUS = 400
EXPECTED_BODY = {"detail": "Invalid activation data"}


def _activate(client: TestClient, authed, public_id: str, claim_code: str):
    return client.post(
        "/api/devices/activate",
        json={"public_id": public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers=authed.headers,
    )


def _unused_valid_public_id(session) -> str:
    from app.repositories.devices import get_device_by_public_id

    for _ in range(10):
        candidate = generate_public_id()
        if get_device_by_public_id(session, candidate) is None:
            return candidate

    raise RuntimeError("Could not find an unused public_id for the test")


def test_nonexistent_public_id_returns_generic_rejection(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    try:
        public_id = _unused_valid_public_id(session)
    finally:
        session.close()

    response = _activate(client, authed, public_id, "AAAA-BBBB-CCCC")

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_already_assigned_device_returns_generic_rejection(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    other = make_authed_user()

    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    first_response = _activate(client, other, device.public_id, claim_code)
    assert first_response.status_code == 200

    response = _activate(client, authed, device.public_id, claim_code)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_missing_claim_code_hash_returns_generic_rejection(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()

    session = session_factory()
    device = Device(
        public_id=generate_public_id(),
        status="pending_activation",
        device_type="qr_nfc_tag",
        claim_code_hash=None,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    public_id = device.public_id
    session.close()

    response = _activate(client, authed, public_id, "AAAA-BBBB-CCCC")

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_wrong_claim_code_returns_generic_rejection(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = _activate(client, authed, device.public_id, "ZZZZ-ZZZZ-ZZZZ")

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY


def test_nonexistent_public_id_does_not_mutate_any_row(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    try:
        public_id = _unused_valid_public_id(session)
        before_count = session.query(Device).count()
    finally:
        session.close()

    _activate(client, authed, public_id, "AAAA-BBBB-CCCC")

    session = session_factory()
    try:
        after_count = session.query(Device).count()
        assert after_count == before_count
    finally:
        session.close()


def test_non_pending_device_is_not_mutated(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    other = make_authed_user()

    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    activate_response = _activate(client, other, device.public_id, claim_code)
    assert activate_response.status_code == 200

    session = session_factory()
    try:
        activated_device = session.get(Device, device.id)
        activated_at_before = activated_device.activated_at
        user_id_before = activated_device.user_id
    finally:
        session.close()

    _activate(client, authed, device.public_id, claim_code)

    session = session_factory()
    try:
        activated_device = session.get(Device, device.id)
        assert activated_device.activated_at == activated_at_before
        assert activated_device.user_id == user_id_before
    finally:
        session.close()


def test_missing_hash_does_not_increment_claim_attempts(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()

    session = session_factory()
    device = Device(
        public_id=generate_public_id(),
        status="pending_activation",
        device_type="qr_nfc_tag",
        claim_code_hash=None,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    public_id = device.public_id
    device_id = device.id
    session.close()

    _activate(client, authed, public_id, "AAAA-BBBB-CCCC")

    session = session_factory()
    try:
        device = session.get(Device, device_id)
        assert device.claim_attempts == 0
    finally:
        session.close()


def test_wrong_claim_code_increments_claim_attempts(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    device_id = device.id
    session.close()

    _activate(client, authed, device.public_id, "ZZZZ-ZZZZ-ZZZZ")

    session = session_factory()
    try:
        device = session.get(Device, device_id)
        assert device.claim_attempts == 1
    finally:
        session.close()


def test_lockout_reached_after_max_attempts_and_then_returns_429(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    for _ in range(5):
        response = _activate(client, authed, device.public_id, "ZZZZ-ZZZZ-ZZZZ")
        assert response.status_code == EXPECTED_STATUS

    session = session_factory()
    try:
        locked_device = session.get(Device, device.id)
        assert locked_device.claim_attempts == 5
        assert locked_device.claim_locked_until is not None
        assert locked_device.claim_locked_until > datetime.now(UTC)
    finally:
        session.close()

    locked_response = _activate(client, authed, device.public_id, claim_code)
    assert locked_response.status_code == 429


def test_correct_claim_while_unlocked_succeeds(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = _activate(client, authed, device.public_id, claim_code)

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_locked_device_still_returns_429_not_unified_400(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    device.claim_attempts = 5
    device.claim_locked_until = datetime.now(UTC) + timedelta(minutes=15)
    session.add(device)
    session.commit()
    session.close()

    response = _activate(client, authed, device.public_id, claim_code)

    assert response.status_code == 429


def test_non_pending_but_unassigned_device_returns_generic_rejection(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    """Aísla `device.status != "pending_activation"` del OR productivo: este
    Device nunca fue asignado a un usuario (user_id sigue None), solo su
    status difiere de pending_activation."""
    authed = make_authed_user()
    claim_code = "AAAA-BBBB-CCCC"

    session = session_factory()
    device = Device(
        public_id=generate_public_id(),
        status="disabled",
        device_type="qr_nfc_tag",
        claim_code_hash=hash_claim_code(claim_code),
        user_id=None,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    public_id = device.public_id
    device_id = device.id
    before = {
        "status": device.status,
        "user_id": device.user_id,
        "claim_attempts": device.claim_attempts,
        "activated_at": device.activated_at,
        "claimed_at": device.claimed_at,
    }
    session.close()

    response = _activate(client, authed, public_id, claim_code)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY

    session = session_factory()
    try:
        after = session.get(Device, device_id)
        assert after.status == before["status"]
        assert after.user_id == before["user_id"]
        assert after.claim_attempts == before["claim_attempts"]
        assert after.activated_at == before["activated_at"]
        assert after.claimed_at == before["claimed_at"]
    finally:
        session.close()


def test_pending_but_already_assigned_device_returns_generic_rejection(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    """Aísla `device.user_id is not None` del OR productivo: este Device
    sigue en status pending_activation, solo su user_id ya está asignado
    (nunca pasó por el flujo real de activación que lo movería a active)."""
    authed = make_authed_user()
    owner = make_authed_user()
    claim_code = "AAAA-BBBB-CCCC"

    session = session_factory()
    device = Device(
        public_id=generate_public_id(),
        status="pending_activation",
        device_type="qr_nfc_tag",
        claim_code_hash=hash_claim_code(claim_code),
        user_id=owner.user.id,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    public_id = device.public_id
    device_id = device.id
    before = {
        "status": device.status,
        "user_id": device.user_id,
        "claim_attempts": device.claim_attempts,
        "activated_at": device.activated_at,
        "claimed_at": device.claimed_at,
    }
    session.close()

    response = _activate(client, authed, public_id, claim_code)

    assert response.status_code == EXPECTED_STATUS
    assert response.json() == EXPECTED_BODY

    session = session_factory()
    try:
        after = session.get(Device, device_id)
        assert after.status == before["status"]
        assert after.user_id == before["user_id"]
        assert after.claim_attempts == before["claim_attempts"]
        assert after.activated_at == before["activated_at"]
        assert after.claimed_at == before["claimed_at"]
    finally:
        session.close()


def test_unauthenticated_request_returns_401(
    client: TestClient, session_factory: sessionmaker
) -> None:
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
    )

    assert response.status_code == 401


def test_unverified_email_returns_403(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user(verified=False)
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = _activate(client, authed, device.public_id, claim_code)

    assert response.status_code == 403


def test_missing_csrf_header_is_rejected(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed"}


def test_wrong_csrf_header_is_rejected(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers={get_settings().csrf_header_name: "not-the-real-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed"}


def test_valid_auth_email_and_csrf_reaches_activation_logic(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = _activate(client, authed, device.public_id, claim_code)

    assert response.status_code == 200
    assert response.json()["status"] == "active"
