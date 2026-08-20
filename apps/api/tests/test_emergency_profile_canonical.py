"""Bloque 4: resolución canónica transitoria de EmergencyProfile."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.repositories.users import create_user
from app.services.emergency_profile_canonical import (
    CanonicalProfileDivergenceError,
    get_canonical_emergency_profile,
)
from app.services.protected_persons import get_or_create_protected_person
from tests.helpers import make_active_profile


def _protected_person(session):
    user = create_user(session, email=f"{uuid4().hex}@example.com", password_hash="x")
    return get_or_create_protected_person(session, user)


def test_zero_active_profiles_returns_none(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        pp = _protected_person(session)
        assert get_canonical_emergency_profile(session, pp) is None
    finally:
        session.close()


def test_single_profile_is_canonical(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        pp = _protected_person(session)
        profile = make_active_profile(session, protected_person_id=pp.id)

        result = get_canonical_emergency_profile(session, pp)

        assert result is not None
        assert result.id == profile.id
    finally:
        session.close()


def test_multiple_equivalent_profiles_resolve_deterministically(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        pp = _protected_person(session)
        older = make_active_profile(session, protected_person_id=pp.id)
        older.created_at = datetime.now(UTC) - timedelta(days=1)
        session.commit()
        newer = make_active_profile(session, protected_person_id=pp.id)

        result_1 = get_canonical_emergency_profile(session, pp)
        result_2 = get_canonical_emergency_profile(session, pp)

        assert result_1.id == older.id
        assert result_2.id == older.id
        assert result_1.id != newer.id
    finally:
        session.close()


def test_soft_deleted_profiles_never_participate(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        pp = _protected_person(session)
        deleted = make_active_profile(session, protected_person_id=pp.id)
        deleted.deleted_at = datetime.now(UTC)
        session.commit()
        active = make_active_profile(session, protected_person_id=pp.id)

        result = get_canonical_emergency_profile(session, pp)

        assert result is not None
        assert result.id == active.id
    finally:
        session.close()


def test_divergent_profiles_fail_closed(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        pp = _protected_person(session)
        make_active_profile(session, protected_person_id=pp.id, display_name="Jane Doe")
        make_active_profile(session, protected_person_id=pp.id, display_name="Different Name")

        with pytest.raises(CanonicalProfileDivergenceError):
            get_canonical_emergency_profile(session, pp)
    finally:
        session.close()
