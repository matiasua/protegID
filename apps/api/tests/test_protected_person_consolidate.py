"""Bloque 5: tests de la migración 0012 (consolidate_active_ep).

Cubre los 10 casos (A-J) pedidos, el round-trip
0011 -> 0012 -> validar -> downgrade -> validar -> upgrade, y la
autocontención de 0012 (no debe importar app.models/app.services).

Todos corren contra la DB de test aislada (ver tests/conftest.py); nunca
tocan development. Cada test empieza ya en HEAD (0012 aplicada por la suite),
downgradea a 0011 para construir el fixture "legacy" (>1 activo /
protected_person_id NULL / lo que corresponda) y luego re-sube a 0012 (o a
head) para observar el comportamiento bajo prueba. `finally` siempre deja la
DB en head, igual que test_protected_person_backfill.py.
"""

import builtins
import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import EmergencyProfile, ProtectedPerson
from app.repositories.users import create_user

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_PRIOR = "0011_backfill_protected_persons"
_TARGET = "0012_consolidate_active_ep"
_MIGRATION_0012_PATH = (
    Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0012_consolidate_active_ep.py"
)

_INDEX_NAME = "uq_emergency_profiles_active_protected_person"

# Most of this file tests the 0012 migration itself (upgrade/downgrade round
# trips against real data) or the partial unique index it creates - not
# incidental fixture setup - so it is not centralized behind a
# db_at_revision_* fixture (see tests/conftest.py for those).
pytestmark = pytest.mark.migration


def _create_user(session) -> object:
    return create_user(
        session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
    )


def _create_protected_person(session, user) -> ProtectedPerson:
    pp = ProtectedPerson(account_user_id=user.id)
    session.add(pp)
    session.commit()
    session.refresh(pp)
    return pp


def _create_profile(session, *, protected_person_id, **overrides) -> EmergencyProfile:
    values = {
        "display_name": "Ana",
        "emergency_contact_name": "Beto",
        "emergency_contact_phone": "123",
        "medical_conditions_none": True,
        "allergies_none": True,
        "medications_none": True,
    }
    values.update(overrides)
    profile = EmergencyProfile(protected_person_id=protected_person_id, **values)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def test_a_single_active_profile_is_left_unchanged(session_factory: sessionmaker) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        profile = _create_profile(session, protected_person_id=pp.id)
        session.close()

        command.upgrade(cfg, _TARGET)

        session = session_factory()
        refreshed = session.get(EmergencyProfile, profile.id)
        assert refreshed.deleted_at is None
        assert refreshed.protected_person_id == pp.id
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_b_two_equivalent_active_profiles_one_stays_active_other_soft_deleted(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        older = _create_profile(session, protected_person_id=pp.id)
        older.created_at = datetime.now(UTC) - timedelta(days=1)
        session.commit()
        newer = _create_profile(session, protected_person_id=pp.id)
        session.close()

        command.upgrade(cfg, _TARGET)

        session = session_factory()
        refreshed_older = session.get(EmergencyProfile, older.id)
        refreshed_newer = session.get(EmergencyProfile, newer.id)
        assert refreshed_older.deleted_at is None
        assert refreshed_newer.deleted_at is not None
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_c_canonical_selection_is_deterministic_created_at_then_id(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        same_ts = datetime.now(UTC) - timedelta(hours=1)
        first = _create_profile(session, protected_person_id=pp.id)
        second = _create_profile(session, protected_person_id=pp.id)
        first.created_at = same_ts
        second.created_at = same_ts
        session.commit()
        expected_canonical_id = min(first.id, second.id)
        expected_shadow_id = max(first.id, second.id)
        session.close()

        command.upgrade(cfg, _TARGET)

        session = session_factory()
        canonical = session.get(EmergencyProfile, expected_canonical_id)
        shadow = session.get(EmergencyProfile, expected_shadow_id)
        assert canonical.deleted_at is None
        assert shadow.deleted_at is not None
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_d_two_divergent_active_profiles_abort_migration_no_partial_writes(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        profile_a = _create_profile(session, protected_person_id=pp.id, display_name="Ana")
        profile_b = _create_profile(session, protected_person_id=pp.id, display_name="Beatriz")
        session.close()

        with pytest.raises(Exception):
            command.upgrade(cfg, _TARGET)

        session = session_factory()
        refreshed_a = session.get(EmergencyProfile, profile_a.id)
        refreshed_b = session.get(EmergencyProfile, profile_b.id)
        # Ninguna fila fue tocada: ambas siguen activas, sin soft-delete.
        assert refreshed_a.deleted_at is None
        assert refreshed_b.deleted_at is None

        # Resolver antes de restaurar head (mismo patrón que 0011).
        session.delete(refreshed_b)
        session.commit()
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_e_preexisting_soft_deleted_profiles_are_left_untouched(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        active = _create_profile(session, protected_person_id=pp.id)
        pre_existing_shadow = _create_profile(session, protected_person_id=pp.id, display_name="Old")
        original_deleted_at = datetime.now(UTC) - timedelta(days=30)
        pre_existing_shadow.deleted_at = original_deleted_at
        session.commit()
        session.close()

        command.upgrade(cfg, _TARGET)

        session = session_factory()
        refreshed_active = session.get(EmergencyProfile, active.id)
        refreshed_shadow = session.get(EmergencyProfile, pre_existing_shadow.id)
        assert refreshed_active.deleted_at is None
        # Timestamp intacto: 0012 nunca reescribe deleted_at de un perfil que
        # ya estaba soft-deleted antes de correr.
        assert refreshed_shadow.deleted_at == original_deleted_at
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_f_protected_person_id_null_aborts_migration(session_factory: sessionmaker) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        profile = EmergencyProfile(
            protected_person_id=None,
            display_name="Sin dueño",
            medical_conditions_none=True,
            allergies_none=True,
            medications_none=True,
        )
        session.add(profile)
        session.commit()
        profile_id = profile.id
        session.close()

        with pytest.raises(RuntimeError, match="protected_person_id"):
            command.upgrade(cfg, _TARGET)

        session = session_factory()
        refreshed = session.get(EmergencyProfile, profile_id)
        assert refreshed.protected_person_id is None

        session.delete(refreshed)
        session.commit()
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_g_protected_person_id_becomes_not_null(engine: sa.Engine) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, _PRIOR)
        command.upgrade(cfg, _TARGET)

        columns = {c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert columns["protected_person_id"]["nullable"] is False
    finally:
        command.upgrade(cfg, "head")


def test_h_second_active_profile_for_same_person_is_rejected(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        _create_profile(session, protected_person_id=pp.id)

        with pytest.raises(sa.exc.IntegrityError):
            _create_profile(session, protected_person_id=pp.id, display_name="Otra")
    finally:
        session.rollback()
        session.close()


def test_i_additional_soft_deleted_profile_for_same_person_is_allowed(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        _create_profile(session, protected_person_id=pp.id)
        # deleted_at va en el INSERT mismo: si primero se insertara activo y
        # luego se soft-deleteara, el INSERT chocaría con el índice parcial
        # (ya hay un activo para este protected_person_id).
        _create_profile(
            session,
            protected_person_id=pp.id,
            display_name="Historic",
            deleted_at=datetime.now(UTC),
        )

        count = session.scalar(
            select(sa.func.count())
            .select_from(EmergencyProfile)
            .where(EmergencyProfile.protected_person_id == pp.id)
        )
        assert count == 2
    finally:
        session.close()


def test_j_one_active_with_multiple_historical_soft_deleted_is_allowed(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        active = _create_profile(session, protected_person_id=pp.id)
        for label in ("First", "Second", "Third"):
            _create_profile(
                session,
                protected_person_id=pp.id,
                display_name=label,
                deleted_at=datetime.now(UTC),
            )

        active_count = session.scalar(
            select(sa.func.count())
            .select_from(EmergencyProfile)
            .where(
                EmergencyProfile.protected_person_id == pp.id,
                EmergencyProfile.deleted_at.is_(None),
            )
        )
        total_count = session.scalar(
            select(sa.func.count())
            .select_from(EmergencyProfile)
            .where(EmergencyProfile.protected_person_id == pp.id)
        )
        assert active_count == 1
        assert total_count == 4
        assert session.get(EmergencyProfile, active.id).deleted_at is None
    finally:
        session.close()


def test_migration_round_trip_0011_to_0012_and_back(
    session_factory: sessionmaker, engine: sa.Engine
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        older = _create_profile(session, protected_person_id=pp.id)
        older.created_at = datetime.now(UTC) - timedelta(days=1)
        session.commit()
        newer = _create_profile(session, protected_person_id=pp.id)
        session.close()

        # upgrade 0011 -> 0012
        command.upgrade(cfg, _TARGET)

        columns = {c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert columns["protected_person_id"]["nullable"] is False
        indexes = {ix["name"] for ix in sa.inspect(engine).get_indexes("emergency_profiles")}
        assert _INDEX_NAME in indexes

        session = session_factory()
        assert session.get(EmergencyProfile, older.id).deleted_at is None
        assert session.get(EmergencyProfile, newer.id).deleted_at is not None
        session.close()

        # downgrade 0012 -> 0011
        command.downgrade(cfg, _PRIOR)

        columns = {c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert columns["protected_person_id"]["nullable"] is True
        indexes = {ix["name"] for ix in sa.inspect(engine).get_indexes("emergency_profiles")}
        assert _INDEX_NAME not in indexes

        session = session_factory()
        # El shadow soft-deleted por 0012 NO se reactiva en el downgrade.
        assert session.get(EmergencyProfile, older.id).deleted_at is None
        assert session.get(EmergencyProfile, newer.id).deleted_at is not None
        session.close()

        # upgrade 0012 again
        command.upgrade(cfg, _TARGET)

        columns = {c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert columns["protected_person_id"]["nullable"] is False
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_downgrade_drops_partial_unique_index(engine: sa.Engine) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, _PRIOR)
        command.upgrade(cfg, _TARGET)

        indexes = {ix["name"] for ix in sa.inspect(engine).get_indexes("emergency_profiles")}
        assert _INDEX_NAME in indexes

        command.downgrade(cfg, _PRIOR)

        indexes = {ix["name"] for ix in sa.inspect(engine).get_indexes("emergency_profiles")}
        assert _INDEX_NAME not in indexes
    finally:
        command.upgrade(cfg, "head")


def test_migration_0012_does_not_import_productive_app_code(monkeypatch) -> None:
    """0012 debe ser autocontenida: no debe importar app.models ni
    app.services, igual que 0011."""
    real_import = builtins.__import__
    blocked_prefixes = ("app.models", "app.services")

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app" and fromlist and any(f in ("models", "services") for f in fromlist):
            raise AssertionError(
                f"0012 migration must not import app.{fromlist!r} (productive code)"
            )
        if any(name == prefix or name.startswith(prefix + ".") for prefix in blocked_prefixes):
            raise AssertionError(f"0012 migration must not import {name!r} (productive code)")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    spec = importlib.util.spec_from_file_location(
        "test_isolated_migration_0012", _MIGRATION_0012_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "upgrade")
    assert hasattr(module, "downgrade")
