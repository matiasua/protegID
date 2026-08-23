"""Bloque 8.4 — PUT /api/emergency-profile ante >1 EmergencyProfile activo.

Post-0012 el invariante de la DB es a lo sumo 1 EmergencyProfile activo por
ProtectedPerson (uq_emergency_profiles_active_protected_person). Si por
corrupción/SQL manual existiera más de uno -- equivalentes o divergentes, da
igual -- el PUT debe fallar cerrado: nunca elige, nunca escribe parcialmente.
Ese estado no es representable a HEAD vía el ORM normal (el índice único lo
impide), así que estos tests corren pinned a 0011 (ver tests/conftest.py
db_at_revision_0011), la última revisión donde >1 activo era construible.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import EmergencyProfile
from app.repositories.users import create_user
from app.services.emergency_profile_canonical import CanonicalProfileDivergenceError
from app.services.protected_persons import get_or_create_protected_person
from tests.helpers import make_active_profile, ready_profile_payload

pytestmark = [pytest.mark.migration, pytest.mark.usefixtures("db_at_revision_0011")]


# --- Divergentes: fail closed, ninguno cambia ---


def test_put_fails_closed_when_active_profiles_diverge(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    protected_person = get_or_create_protected_person(session, authed.user)
    profile_a = make_active_profile(
        session, protected_person_id=protected_person.id, display_name="Name A"
    )
    profile_b = make_active_profile(
        session, protected_person_id=protected_person.id, display_name="Name B"
    )
    session.close()

    response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(display_name="Attempted write"),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 409

    session = session_factory()
    try:
        refreshed_a = session.get(EmergencyProfile, profile_a.id)
        refreshed_b = session.get(EmergencyProfile, profile_b.id)
        assert refreshed_a.display_name == "Name A"
        assert refreshed_b.display_name == "Name B"
    finally:
        session.close()


# --- Equivalentes: fail closed igual. Ya no existe selección canónica ni
#     sincronización de shadows -- >1 activo es siempre una violación de
#     integridad, sean o no equivalentes en contenido. ---


def test_put_fails_closed_when_active_profiles_are_equivalent(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    protected_person = get_or_create_protected_person(session, authed.user)
    first = make_active_profile(session, protected_person_id=protected_person.id)
    second = make_active_profile(session, protected_person_id=protected_person.id)
    session.close()

    response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(display_name="Attempted write"),
        cookies=authed.cookies,
        headers=authed.headers,
    )

    assert response.status_code == 409

    session = session_factory()
    try:
        refreshed_first = session.get(EmergencyProfile, first.id)
        refreshed_second = session.get(EmergencyProfile, second.id)
        assert refreshed_first.display_name != "Attempted write"
        assert refreshed_second.display_name != "Attempted write"
    finally:
        session.close()


def test_get_active_profile_for_write_raises_on_multiple_active_profiles(
    session_factory: sessionmaker,
) -> None:
    from app.services.emergency_profile_canonical import get_active_profile_for_write

    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="x"
        )
        protected_person = get_or_create_protected_person(session, user)
        make_active_profile(
            session, protected_person_id=protected_person.id, display_name="Name A"
        )
        make_active_profile(
            session, protected_person_id=protected_person.id, display_name="Name B"
        )

        with pytest.raises(CanonicalProfileDivergenceError):
            get_active_profile_for_write(session, protected_person)
    finally:
        session.close()


# --- Soft-deleted nunca participa en la resolución que ve el PUT ---


def test_put_does_not_touch_soft_deleted_profiles(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    protected_person = get_or_create_protected_person(session, authed.user)
    active = make_active_profile(session, protected_person_id=protected_person.id)
    deleted = make_active_profile(session, protected_person_id=protected_person.id)
    deleted.deleted_at = datetime.now(UTC)
    session.commit()
    active_id, deleted_id = active.id, deleted.id
    session.close()

    response = client.put(
        "/api/emergency-profile",
        json=ready_profile_payload(display_name="Only active changes"),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200

    session = session_factory()
    try:
        refreshed_active = session.get(EmergencyProfile, active_id)
        refreshed_deleted = session.get(EmergencyProfile, deleted_id)
        assert refreshed_active.display_name == "Only active changes"
        assert refreshed_deleted.display_name != "Only active changes"
    finally:
        session.close()
