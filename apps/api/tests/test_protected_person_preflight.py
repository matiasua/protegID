"""Bloque 3: tests del preflight de solo lectura (app.services.protected_person_preflight).

Cubre los 10 casos pedidos: DB vacía, usuarios sin/con devices, perfiles
equivalentes/divergentes, devices huérfanos, soft-delete, y que el reporte de
divergencia nunca imprime contenido médico completo.

run_preflight/run_consolidation_preflight inspect legacy EmergencyProfile
states (NULL protected_person_id, >1 ACTIVE profile per person) that, as of
0012, can only be constructed against a schema older than 0012's NOT NULL
column / partial unique index. Every test in this file therefore runs
pinned to 0011 - not 0010: nothing here needs anything 0010 has that 0011
doesn't (see tests/conftest.py db_at_revision_0011).
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.models import Device, EmergencyProfile, ProtectedPerson
from app.repositories.emergency_profiles import create_profile
from app.repositories.users import create_user
from app.services.protected_person_preflight import run_consolidation_preflight, run_preflight

pytestmark = [pytest.mark.migration, pytest.mark.usefixtures("db_at_revision_0011")]


def _create_user(session):
    return create_user(
        session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
    )


def _create_device(session, *, user_id=None) -> Device:
    device = Device(user_id=user_id, public_id=f"dev-{uuid4().hex}")
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def test_preflight_on_empty_database(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        report = run_preflight(session)
    finally:
        session.close()

    assert report.users_with_devices == 0
    assert report.devices_without_user == 0
    assert report.profiles_on_orphan_devices == 0
    assert report.users_with_zero_profiles == 0
    assert report.users_with_one_profile == 0
    assert report.users_with_multiple_profiles == 0
    assert report.equivalent_profile_groups == []
    assert report.divergent_profile_groups == []
    assert report.soft_deleted_profiles == 0
    assert report.soft_deleted_devices == 0
    assert report.fk_inconsistencies == []
    assert not report.has_blocking_divergence


def test_user_without_device_is_not_counted(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        _create_user(session)
        report = run_preflight(session)
    finally:
        session.close()

    assert report.users_with_devices == 0
    assert report.users_with_zero_profiles == 0


def test_user_with_device_and_no_profile(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        _create_device(session, user_id=user.id)
        report = run_preflight(session)
    finally:
        session.close()

    assert report.users_with_devices == 1
    assert report.users_with_zero_profiles == 1
    assert report.users_with_one_profile == 0
    assert report.users_with_multiple_profiles == 0


def test_user_with_one_device_and_profile(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        device = _create_device(session, user_id=user.id)
        create_profile(session, device_id=device.id, display_name="Ana")
        report = run_preflight(session)
    finally:
        session.close()

    assert report.users_with_devices == 1
    assert report.users_with_one_profile == 1
    assert report.users_with_zero_profiles == 0


def test_user_with_two_devices_and_a_single_profile(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        device_a = _create_device(session, user_id=user.id)
        _create_device(session, user_id=user.id)
        create_profile(session, device_id=device_a.id, display_name="Ana")
        report = run_preflight(session)
    finally:
        session.close()

    assert report.users_with_devices == 1
    assert report.users_with_one_profile == 1


def test_user_with_two_equivalent_profiles(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        create_profile(
            session,
            device_id=device_a.id,
            display_name="Ana",
            emergency_contact_name="Beto",
            emergency_contact_phone="123",
            medical_conditions_none=True,
            allergies_none=True,
        )
        create_profile(
            session,
            device_id=device_b.id,
            display_name="Ana",
            emergency_contact_name="Beto",
            emergency_contact_phone="123",
            medical_conditions_none=True,
            allergies_none=True,
        )
        report = run_preflight(session)
    finally:
        session.close()

    assert report.users_with_multiple_profiles == 1
    assert len(report.equivalent_profile_groups) == 1
    assert report.divergent_profile_groups == []
    assert not report.has_blocking_divergence


def test_equivalent_profiles_ignore_none_vs_empty_string_representation(
    session_factory: sessionmaker,
) -> None:
    """None, "" y whitespace deben tratarse como el mismo "vacío", sin tocar contenido real."""
    session = session_factory()
    try:
        user = _create_user(session)
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        create_profile(session, device_id=device_a.id, display_name="Ana", notes=None)
        create_profile(session, device_id=device_b.id, display_name="Ana", notes="   ")
        report = run_preflight(session)
    finally:
        session.close()

    assert len(report.equivalent_profile_groups) == 1
    assert report.divergent_profile_groups == []


def test_user_with_divergent_profiles_is_flagged(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        create_profile(session, device_id=device_a.id, display_name="Ana")
        create_profile(session, device_id=device_b.id, display_name="Beatriz")
        report = run_preflight(session)
    finally:
        session.close()

    assert report.has_blocking_divergence
    assert len(report.divergent_profile_groups) == 1
    divergence = report.divergent_profile_groups[0]
    assert divergence.user_id == user.id
    assert "display_name" in divergence.divergent_fields
    assert set(divergence.device_public_ids) == {device_a.public_id, device_b.public_id}


def test_device_without_owner_with_profile_is_orphan_not_divergent(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        device = _create_device(session, user_id=None)
        create_profile(session, device_id=device.id, display_name="Sin dueño")
        report = run_preflight(session)
    finally:
        session.close()

    assert report.devices_without_user == 1
    assert report.profiles_on_orphan_devices == 1
    assert report.users_with_devices == 0
    assert report.divergent_profile_groups == []


def test_soft_deleted_profile_excluded_from_user_profile_counts(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        device = _create_device(session, user_id=user.id)
        profile = create_profile(session, device_id=device.id, display_name="Ana")
        profile.deleted_at = datetime.now(UTC)
        session.commit()

        report = run_preflight(session)
    finally:
        session.close()

    assert report.soft_deleted_profiles == 1
    # El único perfil del usuario está soft-deleted: no cuenta como perfil activo.
    assert report.users_with_zero_profiles == 1
    assert report.users_with_one_profile == 0


def test_divergence_report_does_not_leak_full_medical_content(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        create_profile(
            session,
            device_id=device_a.id,
            display_name="Ana",
            medical_conditions="SUPER-SECRETO-A",
        )
        create_profile(
            session,
            device_id=device_b.id,
            display_name="Ana",
            medical_conditions="SUPER-SECRETO-B",
        )
        report = run_preflight(session)
    finally:
        session.close()

    divergence = report.divergent_profile_groups[0]
    assert "medical_conditions" in divergence.divergent_fields

    report_repr = repr(divergence)
    assert "SUPER-SECRETO-A" not in report_repr
    assert "SUPER-SECRETO-B" not in report_repr

    # field_hashes solo debe contener resúmenes cortos, no el texto real.
    hashes = divergence.field_hashes["medical_conditions"]
    assert all("SUPER-SECRETO" not in h for h in hashes)


# --- Bloque 5 (0012): run_consolidation_preflight, agrupa por protected_person_id ---


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
        device = _create_device(session, user_id=None)
        create_profile(session, device_id=device.id, display_name="Sin dueño")
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
        device = _create_device(session, user_id=user.id)
        create_profile(
            session, protected_person_id=pp.id, device_id=device.id, display_name="Ana"
        )
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
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        create_profile(
            session, protected_person_id=pp.id, device_id=device_a.id, display_name="Ana"
        )
        create_profile(
            session, protected_person_id=pp.id, device_id=device_b.id, display_name="Ana"
        )
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
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        create_profile(
            session, protected_person_id=pp.id, device_id=device_a.id, display_name="Ana"
        )
        create_profile(
            session, protected_person_id=pp.id, device_id=device_b.id, display_name="Beatriz"
        )
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
        device = _create_device(session, user_id=user.id)
        profile = create_profile(
            session, protected_person_id=pp.id, device_id=device.id, display_name="Ana"
        )
        profile.deleted_at = datetime.now(UTC)
        session.commit()
        report = run_consolidation_preflight(session)
    finally:
        session.close()

    assert report.historical_soft_deleted_profiles == 1
    # soft-deleted no cuenta como activo: el ProtectedPerson queda con 0.
    assert report.persons_with_one_active_profile == 0
    assert report.persons_with_multiple_active_profiles == 0
