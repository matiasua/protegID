"""Bloque 8.6: tests de la migración 0013 (drop_ep_device_id).

Cubre: la columna/FK/UNIQUE de device_id desaparecen en 0013, el ciclo
0012 -> 0013 -> 0012 -> 0013 sin error, preservación de datos (la fila, la
relación con ProtectedPerson y el contenido médico sobreviven; solo
desaparece device_id), el caso multi-device (el downgrade nunca elige un
Device automáticamente), las dos secuencias completas pedidas (DB vacía ->
head, y 0012 -> head), y la autocontención de 0013 (no debe importar
app.models/app.services).

Todos corren contra la DB de test aislada (ver tests/conftest.py); nunca
tocan development. `cfg` y `session` se inicializan antes del try en cada
test para que el `finally` (que siempre debe dejar la DB en head) nunca
falle con un NameError si algo revienta antes.
"""

import builtins
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from app.models import Device, EmergencyProfile, ProtectedPerson
from app.repositories.emergency_profiles import create_profile
from app.repositories.users import create_user

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_PRIOR = "0012_consolidate_active_ep"
_TARGET = "0013_drop_ep_device_id"
_MIGRATION_0013_PATH = (
    Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0013_drop_ep_device_id.py"
)

_ACTIVE_INDEX_NAME = "uq_emergency_profiles_active_protected_person"
_LEGACY_FK_NAME = "fk_emergency_profiles_device_id_devices"
_LEGACY_UNIQUE_NAME = "uq_emergency_profiles_device_id"

# Not incidental fixture setup: every test but the self-containment check
# drives command.downgrade/upgrade directly as its subject under test (same
# rationale as test_protected_person_backfill.py / test_protected_person_consolidate.py).
pytestmark = pytest.mark.migration


def _create_user(session):
    return create_user(
        session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
    )


def _create_protected_person(session, user) -> ProtectedPerson:
    pp = ProtectedPerson(account_user_id=user.id)
    session.add(pp)
    session.commit()
    session.refresh(pp)
    return pp


def _create_device(session, *, user_id=None, protected_person_id=None) -> Device:
    device = Device(
        user_id=user_id,
        protected_person_id=protected_person_id,
        public_id=f"dev-{uuid4().hex}",
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def test_device_id_column_is_dropped_at_head(engine: sa.Engine) -> None:
    columns = {c["name"] for c in sa.inspect(engine).get_columns("emergency_profiles")}
    assert "device_id" not in columns
    assert "protected_person_id" in columns


def test_active_partial_unique_index_survives_0013(engine: sa.Engine) -> None:
    """0013 no debe tocar el invariante de 0012 (a lo sumo un EmergencyProfile
    ACTIVE por ProtectedPerson)."""
    indexes = {ix["name"] for ix in sa.inspect(engine).get_indexes("emergency_profiles")}
    assert _ACTIVE_INDEX_NAME in indexes


def test_upgrade_drops_legacy_fk_and_unique_constraint(engine: sa.Engine) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, _PRIOR)

        unique_constraints = sa.inspect(engine).get_unique_constraints("emergency_profiles")
        assert any(uc["column_names"] == ["device_id"] for uc in unique_constraints)
        fks = sa.inspect(engine).get_foreign_keys("emergency_profiles")
        assert any(
            fk["referred_table"] == "devices" and fk["constrained_columns"] == ["device_id"]
            for fk in fks
        )

        command.upgrade(cfg, _TARGET)

        unique_constraints = sa.inspect(engine).get_unique_constraints("emergency_profiles")
        assert not any(uc["column_names"] == ["device_id"] for uc in unique_constraints)
        fks = sa.inspect(engine).get_foreign_keys("emergency_profiles")
        assert not any(fk["constrained_columns"] == ["device_id"] for fk in fks)
    finally:
        command.upgrade(cfg, "head")


def test_migration_round_trip_0012_to_0013_and_back(engine: sa.Engine) -> None:
    """Ciclo 0012 -> 0013 -> 0012 -> 0013 sin error, verificando la columna en
    cada paso (existe/nullable en 0012, no existe en 0013)."""
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, _PRIOR)
        columns = {c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert columns["device_id"]["nullable"] is True

        command.upgrade(cfg, _TARGET)
        columns = {c["name"] for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert "device_id" not in columns

        command.downgrade(cfg, _PRIOR)
        columns = {c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert "device_id" in columns
        assert columns["device_id"]["nullable"] is True

        command.upgrade(cfg, _TARGET)
        columns = {c["name"] for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert "device_id" not in columns
    finally:
        command.upgrade(cfg, "head")


def test_downgrade_restores_device_id_as_null_never_data(
    session_factory: sessionmaker, engine: sa.Engine
) -> None:
    """Downgrade estructural: la columna reaparece NULL, nunca con un valor
    inventado, aunque el profile haya existido con protected_person_id (nunca
    tuvo device_id porque fue creado vía el flujo productivo actual)."""
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        profile = create_profile(session, protected_person_id=pp.id, display_name="Ana")
        profile_id = profile.id
        session.close()

        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        row = session.execute(
            sa.text("SELECT device_id FROM emergency_profiles WHERE id = :id"),
            {"id": profile_id},
        ).first()
        assert row is not None
        assert row.device_id is None
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_upgrade_preserves_profile_row_and_medical_content(
    session_factory: sessionmaker,
) -> None:
    """La fila, la relación con ProtectedPerson y el contenido médico
    sobreviven a 0013: solo desaparece la asociación legacy device_id."""
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        device = _create_device(session, user_id=user.id, protected_person_id=pp.id)
        profile = create_profile(
            session,
            protected_person_id=pp.id,
            display_name="Ana",
            medical_conditions="Asma",
            emergency_contact_name="Beto",
            emergency_contact_phone="+56911111111",
        )
        # Fila legacy con device_id poblado, tal como podría existir en una DB
        # real que nunca pasó por el bridge C-lite hasta este punto.
        session.execute(
            sa.text(
                "UPDATE emergency_profiles SET device_id = :device_id WHERE id = :id"
            ),
            {"device_id": device.id, "id": profile.id},
        )
        session.commit()
        profile_id, device_id, pp_id = profile.id, device.id, pp.id
        session.close()

        command.upgrade(cfg, _TARGET)

        session = session_factory()
        refreshed_profile = session.get(EmergencyProfile, profile_id)
        assert refreshed_profile is not None
        assert refreshed_profile.protected_person_id == pp_id
        assert refreshed_profile.display_name == "Ana"
        assert refreshed_profile.medical_conditions == "Asma"
        assert refreshed_profile.emergency_contact_name == "Beto"
        assert refreshed_profile.emergency_contact_phone == "+56911111111"

        refreshed_device = session.get(Device, device_id)
        assert refreshed_device is not None
        assert refreshed_device.protected_person_id == pp_id
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_multi_device_downgrade_never_picks_a_device(
    session_factory: sessionmaker, engine: sa.Engine
) -> None:
    """ProtectedPerson con 2 Devices y 1 EmergencyProfile: tras
    downgrade 0013 -> 0012, device_id debe ser NULL - nunca A ni B."""
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = _create_user(session)
        pp = _create_protected_person(session, user)
        device_a = _create_device(session, user_id=user.id, protected_person_id=pp.id)
        device_b = _create_device(session, user_id=user.id, protected_person_id=pp.id)
        profile = create_profile(session, protected_person_id=pp.id, display_name="Ana")
        profile_id = profile.id
        session.close()

        command.downgrade(cfg, _PRIOR)

        session = session_factory()
        row = session.execute(
            sa.text("SELECT device_id FROM emergency_profiles WHERE id = :id"),
            {"id": profile_id},
        ).first()
        assert row is not None
        assert row.device_id is None
        assert row.device_id != device_a.id
        assert row.device_id != device_b.id
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_migration_from_empty_database_reaches_head(engine: sa.Engine) -> None:
    """La cadena completa 0001 -> ... -> 0012 -> 0013 corre sin error desde
    una DB vacía (base), no solo desde una ya migrada."""
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")

        columns = {c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert "device_id" not in columns
        assert columns["protected_person_id"]["nullable"] is False

        indexes = {ix["name"] for ix in sa.inspect(engine).get_indexes("emergency_profiles")}
        assert _ACTIVE_INDEX_NAME in indexes
    finally:
        command.upgrade(cfg, "head")


def test_migration_from_0012_reaches_head(engine: sa.Engine) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, _PRIOR)
        command.upgrade(cfg, "head")

        columns = {c["name"] for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert "device_id" not in columns
    finally:
        command.upgrade(cfg, "head")


def test_migration_0013_does_not_import_productive_app_code(monkeypatch) -> None:
    """0013 debe ser autocontenida: no debe importar app.models ni
    app.services, igual que 0011/0012."""
    real_import = builtins.__import__
    blocked_prefixes = ("app.models", "app.services")

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app" and fromlist and any(
            f in ("models", "services") for f in fromlist
        ):
            raise AssertionError(
                f"0013 migration must not import app.{fromlist!r} (productive code)"
            )
        if any(name == prefix or name.startswith(prefix + ".") for prefix in blocked_prefixes):
            raise AssertionError(f"0013 migration must not import {name!r} (productive code)")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    spec = importlib.util.spec_from_file_location(
        "test_isolated_migration_0013", _MIGRATION_0013_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # would raise AssertionError above if it tried

    assert hasattr(module, "upgrade")
    assert hasattr(module, "downgrade")
