"""Bloque 4: activación de Device asocia ProtectedPerson server-side."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import Device, ProtectedPerson
from tests.helpers import create_pending_device_with_claim_code


def _activate(client: TestClient, authed, device, claim_code: str):
    return client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": claim_code},
        cookies=authed.cookies,
        headers=authed.headers,
    )


def test_first_device_activation_creates_protected_person(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = _activate(client, authed, device, claim_code)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["user_id"] == str(authed.user.id)

    session = session_factory()
    try:
        protected_person = session.scalar(
            select(ProtectedPerson).where(
                ProtectedPerson.account_user_id == authed.user.id
            )
        )
        assert protected_person is not None
        device = session.get(Device, device.id)
        assert device.protected_person_id == protected_person.id
    finally:
        session.close()


def test_second_device_activation_reuses_same_protected_person(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()

    session = session_factory()
    device_a, claim_a = create_pending_device_with_claim_code(session)
    device_b, claim_b = create_pending_device_with_claim_code(session)
    session.close()

    response_a = _activate(client, authed, device_a, claim_a)
    response_b = _activate(client, authed, device_b, claim_b)

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    session = session_factory()
    try:
        protected_persons = list(
            session.scalars(
                select(ProtectedPerson).where(
                    ProtectedPerson.account_user_id == authed.user.id
                )
            )
        )
        assert len(protected_persons) == 1

        device_a = session.get(Device, device_a.id)
        device_b = session.get(Device, device_b.id)
        assert device_a.protected_person_id == protected_persons[0].id
        assert device_b.protected_person_id == protected_persons[0].id
    finally:
        session.close()


def test_activation_transaction_leaves_user_id_and_protected_person_id_coherent(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, claim_code = create_pending_device_with_claim_code(session)
    session.close()

    _activate(client, authed, device, claim_code)

    session = session_factory()
    try:
        device = session.get(Device, device.id)
        assert device.user_id == authed.user.id
        assert device.protected_person_id is not None
    finally:
        session.close()


def test_invalid_claim_code_does_not_activate_or_create_protected_person(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device, _claim_code = create_pending_device_with_claim_code(session)
    session.close()

    response = client.post(
        "/api/devices/activate",
        json={"public_id": device.public_id, "claim_code": "ZZZZ-ZZZZ-ZZZZ"},
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 400

    session = session_factory()
    try:
        protected_person = session.scalar(
            select(ProtectedPerson).where(
                ProtectedPerson.account_user_id == authed.user.id
            )
        )
        assert protected_person is None
    finally:
        session.close()
