"""Bloque 4 — capa TRANSITIONAL de sincronización canonical/shadows.

Mientras pueda haber más de un EmergencyProfile activo equivalente para el
mismo ProtectedPerson, todo PUT al canonical debe propagar los mismos campos
a los shadows activos equivalentes, atómicamente, o fallar cerrado si
divergen. Ver app.services.emergency_profile_canonical y
app.services.emergency_profiles.put_account_profile.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import EmergencyProfile
from app.repositories.users import create_user
from app.schemas.emergency_profile import EmergencyProfileUpdate
from app.services.emergency_profile_canonical import CanonicalProfileDivergenceError
from app.services.emergency_profiles import put_account_profile
from app.services.protected_persons import get_or_create_protected_person
from tests.helpers import (
    create_pending_device_with_claim_code,
    make_active_profile,
    ready_profile_payload,
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


# --- A: dos perfiles equivalentes, PUT via account, ambos siguen equivalentes ---


def test_put_account_profile_keeps_two_equivalent_active_profiles_in_sync(
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
        json=ready_profile_payload(display_name="Synced via account PUT"),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200

    session = session_factory()
    try:
        refreshed_first = session.get(EmergencyProfile, first.id)
        refreshed_second = session.get(EmergencyProfile, second.id)
        assert refreshed_first.display_name == "Synced via account PUT"
        assert refreshed_second.display_name == "Synced via account PUT"
        assert refreshed_first.deleted_at is None
        assert refreshed_second.deleted_at is None
    finally:
        session.close()


# --- B: PUT via legacy adapter Device B, canonical y shadow quedan sincronizados ---


def test_put_via_legacy_device_b_syncs_canonical_and_shadow(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    authed = make_authed_user()
    session = session_factory()
    device_a, claim_a = create_pending_device_with_claim_code(session)
    device_b, claim_b = create_pending_device_with_claim_code(session)
    session.close()

    activated_a = _activate(client, authed, device_a, claim_a)
    _activate(client, authed, device_b, claim_b)

    session = session_factory()
    protected_person = get_or_create_protected_person(session, authed.user)
    first = make_active_profile(session, protected_person_id=protected_person.id)
    second = make_active_profile(session, protected_person_id=protected_person.id)
    session.close()

    response = client.put(
        f"/api/devices/{activated_a['id']}/emergency-profile",
        json=ready_profile_payload(display_name="Set via device B path"),
        cookies=authed.cookies,
        headers=authed.headers,
    )
    assert response.status_code == 200

    session = session_factory()
    try:
        refreshed_first = session.get(EmergencyProfile, first.id)
        refreshed_second = session.get(EmergencyProfile, second.id)
        assert refreshed_first.display_name == "Set via device B path"
        assert refreshed_second.display_name == "Set via device B path"
    finally:
        session.close()


# --- C: dos perfiles divergentes antes del PUT -> fail closed, ninguno cambia ---


def test_put_fails_closed_when_active_profiles_diverge_before_write(
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


def test_get_canonical_and_shadow_profiles_for_write_raises_on_divergence(
    session_factory: sessionmaker,
) -> None:
    from app.services.emergency_profile_canonical import (
        get_canonical_and_shadow_profiles_for_write,
    )

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
            get_canonical_and_shadow_profiles_for_write(session, protected_person)
    finally:
        session.close()


# --- D: fallo durante actualización de un shadow -> rollback completo, atómico ---


def test_shadow_sync_is_atomic_rollback_leaves_canonical_untouched(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="x"
        )
        protected_person = get_or_create_protected_person(session, user)
        canonical = make_active_profile(
            session, protected_person_id=protected_person.id, display_name="Original"
        )
        shadow = make_active_profile(
            session, protected_person_id=protected_person.id, display_name="Original"
        )
        canonical_id, shadow_id = canonical.id, shadow.id

        def _failing_commit() -> None:
            raise IntegrityError("simulated failure during shadow sync", None, None)

        monkeypatch.setattr(session, "commit", _failing_commit)

        with pytest.raises(IntegrityError):
            put_account_profile(
                session, user, EmergencyProfileUpdate(display_name="Updated")
            )

        session.rollback()
    finally:
        session.close()

    fresh = session_factory()
    try:
        refreshed_canonical = fresh.get(EmergencyProfile, canonical_id)
        refreshed_shadow = fresh.get(EmergencyProfile, shadow_id)
        assert refreshed_canonical.display_name == "Original"
        assert refreshed_shadow.display_name == "Original"
    finally:
        fresh.close()


# --- No sincronizar soft-deleted ---


def test_soft_deleted_profiles_are_never_synced(
    client: TestClient, make_authed_user, session_factory: sessionmaker
) -> None:
    from datetime import UTC, datetime

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
