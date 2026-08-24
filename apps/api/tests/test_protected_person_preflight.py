"""Bloque 5 (0012): tests de app.services.protected_person_preflight.run_consolidation_preflight.

run_consolidation_preflight inspecciona EmergencyProfile ACTIVOS agrupados
por protected_person_id, la precondición real que 0012 valida (NULL count,
>1 activo, equivalencia/divergencia entre ellos). Corre pinneado a 0011 (no
0010) porque necesita protected_person_id ya poblable pero sin la NOT NULL
constraint ni el partial unique index que 0012 agrega.

Bloque 8.6 retiró la mitad "Bloque 3" de este módulo (run_preflight, que
agrupaba por User vía EmergencyProfile.device_id): su único propósito era
auditar una DB anterior a la migración 0011, que ya corrió en toda DB de
este linaje. Ver docs/ai-rules.md.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.models import ProtectedPerson
from app.repositories.emergency_profiles import create_profile
from app.repositories.users import create_user
from app.services.protected_person_preflight import run_consolidation_preflight

pytestmark = [pytest.mark.migration, pytest.mark.usefixtures("db_at_revision_0011")]


def _create_user(session):
    return create_user(
        session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
    )


def _create_pp(session, user) -> ProtectedPerson:
    pp = ProtectedPerson(account_user_id=user.id)
    session.add(pp)
    session.commit()
    session.refresh(pp)
    return pp


def test_consolidation_preflight_flags_null_protected_person_id(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        create_profile(session, display_name="Sin dueño")
        report = run_consolidation_preflight(session)
    finally:
        session.close()

    assert report.protected_person_id_null_count == 1
    assert not report.is_safe_to_consolidate


def test_consolidation_preflight_single_active_profile(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_pp(session, user)
        create_profile(session, protected_person_id=pp.id, display_name="Ana")
        report = run_consolidation_preflight(session)
    finally:
        session.close()

    assert report.persons_with_one_active_profile == 1
    assert report.persons_with_multiple_active_profiles == 0
    assert report.is_safe_to_consolidate


def test_consolidation_preflight_equivalent_active_group(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_pp(session, user)
        create_profile(session, protected_person_id=pp.id, display_name="Ana")
        create_profile(session, protected_person_id=pp.id, display_name="Ana")
        report = run_consolidation_preflight(session)
    finally:
        session.close()

    assert report.persons_with_multiple_active_profiles == 1
    assert len(report.equivalent_active_groups) == 1
    assert report.divergent_active_groups == []
    assert report.is_safe_to_consolidate


def test_consolidation_preflight_divergent_active_group_is_blocking(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_pp(session, user)
        create_profile(session, protected_person_id=pp.id, display_name="Ana")
        create_profile(session, protected_person_id=pp.id, display_name="Beatriz")
        report = run_consolidation_preflight(session)
    finally:
        session.close()

    assert report.has_blocking_divergence
    assert not report.is_safe_to_consolidate
    divergence = report.divergent_active_groups[0]
    assert divergence.protected_person_id == pp.id
    assert "display_name" in divergence.divergent_fields


def test_consolidation_preflight_counts_historical_soft_deleted(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_pp(session, user)
        profile = create_profile(session, protected_person_id=pp.id, display_name="Ana")
        profile.deleted_at = datetime.now(UTC)
        session.commit()
        report = run_consolidation_preflight(session)
    finally:
        session.close()

    assert report.historical_soft_deleted_profiles == 1
    # soft-deleted no cuenta como activo: el ProtectedPerson queda con 0.
    assert report.persons_with_one_active_profile == 0
    assert report.persons_with_multiple_active_profiles == 0
