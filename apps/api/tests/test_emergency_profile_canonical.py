"""Bloque 8.4: resolución canónica de EmergencyProfile.

Post-0012 el invariante de la DB es a lo sumo 1 EmergencyProfile activo por
ProtectedPerson (uq_emergency_profiles_active_protected_person). El resolver
es 0/1/fail-closed; no elige entre >1 candidatos, sean equivalentes o
divergentes. Ese estado >1 no es representable a HEAD vía el ORM normal (el
índice único lo impide), así que este módulo corre pinned a 0011, la última
revisión donde >1 activo era construible (see tests/conftest.py
db_at_revision_0011)."""

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

pytestmark = [pytest.mark.migration, pytest.mark.usefixtures("db_at_revision_0011")]


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


def test_multiple_equivalent_profiles_fail_closed(
    session_factory: sessionmaker,
) -> None:
    """>1 activo es siempre una violación de integridad, incluso si su
    contenido es idéntico: el resolver no compara equivalencia ni elige un
    ganador determinístico. Eso era comportamiento transitorio, retirado tras
    0012 (ver Bloque 8.4)."""
    session = session_factory()
    try:
        pp = _protected_person(session)
        older = make_active_profile(session, protected_person_id=pp.id)
        older.created_at = datetime.now(UTC) - timedelta(days=1)
        session.commit()
        make_active_profile(session, protected_person_id=pp.id)

        with pytest.raises(CanonicalProfileDivergenceError):
            get_canonical_emergency_profile(session, pp)
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
