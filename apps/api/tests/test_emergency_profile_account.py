"""Bloque 4: endpoints account-scoped GET/PUT/status de EmergencyProfile."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import Device, ProtectedPerson
from tests.helpers import public_ready_payload, ready_profile_payload


def test_get_account_profile_without_profile_returns_404_and_creates_nothing(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()

    response = client.get("/api/emergency-profile", cookies=authed.cookies)

    assert response.status_code == 404

    session = session_factory()
    try:
        rows = list(
            session.scalars(
                select(ProtectedPerson).where(
                    ProtectedPerson.account_user_id == authed.user.id
                )
            )
        )
        assert rows == []
    finally:
        session.close()


def test_put_account_profile_without_device_creates_person_and_profile(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()

    response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "device_id" not in body
    assert body["display_name"] == "Jane Doe"

    session = session_factory()
    try:
        protected_person = session.scalar(
            select(ProtectedPerson).where(
                ProtectedPerson.account_user_id == authed.user.id
            )
        )
        assert protected_person is not None

        devices = list(
            session.scalars(select(Device).where(Device.user_id == authed.user.id))
        )
        assert devices == []
    finally:
        session.close()


def test_get_after_put_returns_same_profile(
    client: TestClient, make_authed_user
) -> None:
    authed = make_authed_user()

    put_response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert put_response.status_code == 200
    created_id = put_response.json()["id"]

    get_response = client.get("/api/emergency-profile", cookies=authed.cookies)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_id


def test_put_updates_existing_canonical_profile_in_place(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()

    first = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    first_id = first.json()["id"]

    second = client.put(
        "/api/emergency-profile",
        json={"display_name": "Updated Name"},
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert second.status_code == 200
    assert second.json()["id"] == first_id
    assert second.json()["display_name"] == "Updated Name"

    session = session_factory()
    try:
        protected_person = session.scalar(
            select(ProtectedPerson).where(
                ProtectedPerson.account_user_id == authed.user.id
            )
        )
        assert protected_person is not None
    finally:
        session.close()


def test_publication_requires_readiness_and_valid_consent(
    client: TestClient, make_authed_user
) -> None:
    authed = make_authed_user()

    response = client.put(
        "/api/emergency-profile",
        json={"is_public": True, "display_name": "Incomplete"},
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 422


def test_publication_succeeds_when_ready_and_consented(
    client: TestClient, make_authed_user
) -> None:
    authed = make_authed_user()

    response = client.put(
        "/api/emergency-profile",
        json=public_ready_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 200
    assert response.json()["is_public"] is True


def test_status_before_profile_exists_returns_200_incomplete(
    client: TestClient, make_authed_user
) -> None:
    authed = make_authed_user()

    response = client.get("/api/emergency-profile/status", cookies=authed.cookies)

    assert response.status_code == 200
    body = response.json()
    assert body["readiness"]["is_ready"] is False
    assert body["publication_eligibility"]["can_publish"] is False


def test_status_reflects_ready_profile(
    client: TestClient, make_authed_user
) -> None:
    authed = make_authed_user()
    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    response = client.get("/api/emergency-profile/status", cookies=authed.cookies)

    assert response.status_code == 200
    body = response.json()
    assert body["readiness"]["is_ready"] is True
    assert body["publication_eligibility"]["profile_ready"] is True
    assert body["publication_eligibility"]["consent_valid"] is False


def _soft_delete_protected_person(session_factory: sessionmaker, user_id) -> None:
    session = session_factory()
    try:
        protected_person = session.scalar(
            select(ProtectedPerson).where(ProtectedPerson.account_user_id == user_id)
        )
        protected_person.deleted_at = datetime.now(UTC)
        session.commit()
    finally:
        session.close()


def test_soft_deleted_protected_person_get_is_unavailable(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    _soft_delete_protected_person(session_factory, authed.user.id)

    response = client.get("/api/emergency-profile", cookies=authed.cookies)

    assert response.status_code == 404


def test_soft_deleted_protected_person_put_does_not_recreate(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    _soft_delete_protected_person(session_factory, authed.user.id)

    response = client.put(
        "/api/emergency-profile",
        json={"display_name": "Should not work"},
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 409

    session = session_factory()
    try:
        rows = list(
            session.scalars(
                select(ProtectedPerson).where(
                    ProtectedPerson.account_user_id == authed.user.id
                )
            )
        )
        assert len(rows) == 1
        assert rows[0].deleted_at is not None
    finally:
        session.close()


def test_soft_deleted_protected_person_status_is_unavailable(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    _soft_delete_protected_person(session_factory, authed.user.id)

    response = client.get("/api/emergency-profile/status", cookies=authed.cookies)

    assert response.status_code == 404
