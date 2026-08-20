"""Bloque 3: tests de la migración 0011 (backfill bridge hacia ProtectedPerson).

Cubre los 8 casos de backfill pedidos, el round-trip
0010 -> preflight -> 0011 -> validar -> downgrade -> validar -> upgrade, y los
ajustes pedidos en la revisión post-aprobación:
  - soft-deleted profiles SÍ reciben protected_person_id si su ownership es
    determinista (pero siguen sin participar en el cálculo de divergencia);
  - el downgrade de 0011 preserva las filas de ProtectedPerson;
  - el downgrade solo restaura device_id NOT NULL si es seguro, con fail-fast
    explícito si no lo es;
  - 0011 es autocontenida: no depende de importar app.models/app.services.

Todos corren contra la DB de test aislada (ver tests/conftest.py); nunca tocan
development. `cfg` y `session` se inicializan antes del try en cada test para
que el `finally` (que siempre debe dejar la DB en head) nunca falle con un
NameError si algo revienta antes.
"""

import builtins
import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import Device, EmergencyProfile, ProtectedPerson
from app.repositories.emergency_profiles import create_profile, get_profile_by_device_id
from app.repositories.users import create_user

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_MIGRATION_0011_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "0011_backfill_protected_persons.py"
)

# This whole file tests the 0011 migration itself (upgrade/downgrade round
# trips against real data), not incidental fixture setup - every test but
# the self-containment check drives command.downgrade/upgrade directly as
# its subject under test, so it is not centralized behind a
# db_at_revision_* fixture (see tests/conftest.py for those).
pytestmark = pytest.mark.migration


def _create_device(session, *, user_id=None, status: str = "active") -> Device:
    device = Device(user_id=user_id, public_id=f"dev-{uuid4().hex}", status=status)
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def test_backfill_creates_a_single_protected_person_per_user(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        _create_device(session, user_id=user.id)
        _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        protected_persons = list(
            session.scalars(
                select(ProtectedPerson).where(ProtectedPerson.account_user_id == user.id)
            )
        )
        assert len(protected_persons) == 1
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_backfill_points_multiple_devices_of_same_user_to_same_protected_person(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        refreshed_a = session.get(Device, device_a.id)
        refreshed_b = session.get(Device, device_b.id)

        assert refreshed_a.protected_person_id is not None
        assert refreshed_a.protected_person_id == refreshed_b.protected_person_id
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_backfill_assigns_protected_person_id_to_legacy_profile(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = _create_device(session, user_id=user.id)
        session.close()

        # protected_person_id is NOT NULL as of 0012: the legacy fixture
        # (a profile with no protected_person_id at all) can only be
        # constructed against a schema older than 0012.
        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        profile = create_profile(session, device_id=device.id, display_name="Ana")
        session.close()

        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        refreshed_device = session.get(Device, device.id)
        refreshed_profile = session.get(EmergencyProfile, profile.id)

        assert refreshed_profile.protected_person_id is not None
        assert refreshed_profile.protected_person_id == refreshed_device.protected_person_id
    finally:
        session.close()
        command.upgrade(cfg, "head")


@pytest.mark.parametrize("status", ["lost", "disabled", "active", "pending_activation"])
def test_backfill_associates_devices_regardless_of_status(
    session_factory: sessionmaker, status: str
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = _create_device(session, user_id=user.id, status=status)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        refreshed_device = session.get(Device, device.id)
        assert refreshed_device.protected_person_id is not None
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_account_user_id_stays_unique_after_backfill(
    session_factory: sessionmaker, engine: sa.Engine
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        inspector = sa.inspect(engine)
        unique_constraints = inspector.get_unique_constraints("protected_persons")
        assert any(
            uc["column_names"] == ["account_user_id"] for uc in unique_constraints
        )
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_device_id_column_still_present_after_backfill(engine: sa.Engine) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        columns = {c["name"] for c in sa.inspect(engine).get_columns("emergency_profiles")}
        assert "device_id" in columns
    finally:
        command.upgrade(cfg, "head")


def test_device_id_becomes_nullable_after_backfill(engine: sa.Engine) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        columns = {
            c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")
        }
        assert columns["device_id"]["nullable"] is True
    finally:
        command.upgrade(cfg, "head")


def test_legacy_backend_can_still_read_profile_by_device_id_after_backfill(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        create_profile(session, device_id=device.id, display_name="Ana")
        session.close()

        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        profile = get_profile_by_device_id(session, device.id)
        assert profile is not None
        assert profile.display_name == "Ana"
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_backfill_aborts_on_divergent_profiles_and_writes_nothing(
    session_factory: sessionmaker, engine: sa.Engine
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device_a = _create_device(session, user_id=user.id)
        device_b = _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        create_profile(session, device_id=device_a.id, display_name="Ana")
        create_profile(session, device_id=device_b.id, display_name="Beatriz")
        session.close()

        with pytest.raises(Exception):
            command.upgrade(cfg, "0011_backfill_protected_persons")

        inspector = sa.inspect(engine)
        # La migración debe haber abortado: seguimos en 0010, sin la tabla
        # nueva poblada ni el device_id nullable.
        assert "protected_persons" in inspector.get_table_names()
        session = session_factory()
        assert session.scalar(select(sa.func.count()).select_from(ProtectedPerson)) == 0

        # Resolver la divergencia manualmente antes de restaurar head: si no,
        # el propio `command.upgrade(cfg, "head")` del finally volvería a
        # disparar el mismo fail-fast (correcto, pero rompería el cleanup
        # autouse de conftest, que necesita la DB en head al final del test).
        session.execute(sa.delete(EmergencyProfile).where(EmergencyProfile.device_id == device_b.id))
        session.commit()
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_migration_round_trip_0010_to_0011_and_back(
    session_factory: sessionmaker, engine: sa.Engine
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        profile = create_profile(session, device_id=device.id, display_name="Ana")
        session.close()

        # upgrade 0010 -> 0011
        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        refreshed_device = session.get(Device, device.id)
        refreshed_profile = session.get(EmergencyProfile, profile.id)
        assert refreshed_device.protected_person_id is not None
        assert refreshed_profile.protected_person_id is not None
        protected_person_id = refreshed_device.protected_person_id
        session.close()

        # downgrade 0011 -> 0010
        command.downgrade(cfg, "0010_add_protected_persons")

        columns = {
            c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")
        }
        assert columns["device_id"]["nullable"] is False

        session = session_factory()
        # Las asociaciones nuevas se revierten...
        reverted_device = session.get(Device, device.id)
        reverted_profile = session.get(EmergencyProfile, profile.id)
        assert reverted_device.protected_person_id is None
        assert reverted_profile.protected_person_id is None
        # ...pero la fila de ProtectedPerson en sí se conserva (0011 no la borra).
        preserved = session.get(ProtectedPerson, protected_person_id)
        assert preserved is not None
        assert preserved.account_user_id == user.id
        # device_id-based legacy read still works after the round trip.
        legacy_profile = get_profile_by_device_id(session, device.id)
        assert legacy_profile is not None
        assert legacy_profile.display_name == "Ana"
        session.close()

        # upgrade 0011 again
        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        refreshed_device = session.get(Device, device.id)
        refreshed_profile = session.get(EmergencyProfile, profile.id)
        assert refreshed_device.protected_person_id is not None
        assert refreshed_profile.protected_person_id is not None
        # Re-asociado al MISMO ProtectedPerson preservado, no a uno nuevo.
        assert refreshed_device.protected_person_id == protected_person_id
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_downgrade_preserves_protected_person_rows(
    session_factory: sessionmaker,
) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        before_count = session.scalar(select(sa.func.count()).select_from(ProtectedPerson))
        assert before_count == 1
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        after_count = session.scalar(select(sa.func.count()).select_from(ProtectedPerson))
        assert after_count == before_count == 1
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_downgrade_restores_device_id_not_null_when_safe(engine: sa.Engine) -> None:
    cfg = Config(str(_ALEMBIC_INI))
    try:
        command.downgrade(cfg, "0010_add_protected_persons")
        command.upgrade(cfg, "0011_backfill_protected_persons")

        columns = {
            c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")
        }
        assert columns["device_id"]["nullable"] is True

        command.downgrade(cfg, "0010_add_protected_persons")

        columns = {
            c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")
        }
        assert columns["device_id"]["nullable"] is False
    finally:
        command.upgrade(cfg, "head")


def test_soft_deleted_profile_receives_protected_person_id_when_ownership_determined(
    session_factory: sessionmaker,
) -> None:
    """RELATIONAL BACKFILL: un perfil soft-deleted con ownership determinista
    (device_id -> Device.user_id -> ProtectedPerson) SÍ recibe protected_person_id,
    aunque esté soft-deleted. Soft-delete es historia, no ausencia de dueño."""
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        profile = create_profile(session, device_id=device.id, display_name="Ana")
        profile.deleted_at = datetime.now(UTC)
        session.commit()
        session.close()

        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        refreshed_device = session.get(Device, device.id)
        refreshed_profile = session.get(EmergencyProfile, profile.id)
        assert refreshed_profile.deleted_at is not None
        assert refreshed_profile.protected_person_id is not None
        assert refreshed_profile.protected_person_id == refreshed_device.protected_person_id
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_soft_deleted_divergent_sibling_does_not_block_migration_and_still_gets_backfilled(
    session_factory: sessionmaker,
) -> None:
    """Un usuario con un perfil ACTIVO y un perfil SOFT-DELETED de contenido
    distinto no debe abortar la migración (solo activos entran a la
    comparación de divergencia), y ambos perfiles deben quedar backfilled."""
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device_active = _create_device(session, user_id=user.id)
        device_deleted = _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        active_profile = create_profile(
            session, device_id=device_active.id, display_name="Ana"
        )
        deleted_profile = create_profile(
            session, device_id=device_deleted.id, display_name="Nombre viejo distinto"
        )
        deleted_profile.deleted_at = datetime.now(UTC)
        session.commit()
        session.close()

        # No debe lanzar: la divergencia solo se evalúa entre perfiles activos,
        # y aquí solo hay uno.
        command.upgrade(cfg, "0011_backfill_protected_persons")

        session = session_factory()
        refreshed_active = session.get(EmergencyProfile, active_profile.id)
        refreshed_deleted = session.get(EmergencyProfile, deleted_profile.id)
        assert refreshed_active.protected_person_id is not None
        assert refreshed_deleted.protected_person_id is not None
        assert refreshed_active.protected_person_id == refreshed_deleted.protected_person_id
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_downgrade_aborts_when_device_id_null_exists(
    session_factory: sessionmaker, engine: sa.Engine
) -> None:
    """Simula un perfil account-scoped (device_id IS NULL) creado bajo 0011
    y confirma que el downgrade se niega a restaurar la NOT NULL constraint."""
    cfg = Config(str(_ALEMBIC_INI))
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = _create_device(session, user_id=user.id)
        session.close()

        command.downgrade(cfg, "0010_add_protected_persons")

        session = session_factory()
        profile = create_profile(session, device_id=device.id, display_name="Ana")
        session.close()

        command.upgrade(cfg, "0011_backfill_protected_persons")

        # Simula (fuera del código productivo, que todavía no crea esto) un
        # perfil account-scoped: device_id NULL, solo posible desde 0011 en
        # adelante porque la columna ya es nullable.
        session = session_factory()
        session.execute(
            sa.update(EmergencyProfile)
            .where(EmergencyProfile.id == profile.id)
            .values(device_id=None)
        )
        session.commit()
        session.close()

        with pytest.raises(RuntimeError, match="device_id"):
            command.downgrade(cfg, "0010_add_protected_persons")

        # La DB debe seguir en 0011 (head): el guard abortó antes de tocar el
        # esquema, no hace falta reparar nada para el cleanup autouse.
        columns = {
            c["name"]: c for c in sa.inspect(engine).get_columns("emergency_profiles")
        }
        assert columns["device_id"]["nullable"] is True
    finally:
        session.close()
        command.upgrade(cfg, "head")


def test_migration_0011_does_not_import_productive_app_code(monkeypatch) -> None:
    """0011 debe ser autocontenida: no debe importar app.models ni
    app.services, para que su comportamiento no cambie si esos módulos
    evolucionan en el futuro. Se ejecuta el import guardado con un
    `__import__` interceptado en vez de solo grepear el texto, para probar
    de verdad que cargar el módulo no dispara esos imports."""
    real_import = builtins.__import__
    blocked_prefixes = ("app.models", "app.services")

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app" and fromlist and any(
            f in ("models", "services") for f in fromlist
        ):
            raise AssertionError(
                f"0011 migration must not import app.{fromlist!r} (productive code)"
            )
        if any(name == prefix or name.startswith(prefix + ".") for prefix in blocked_prefixes):
            raise AssertionError(f"0011 migration must not import {name!r} (productive code)")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    spec = importlib.util.spec_from_file_location(
        "test_isolated_migration_0011", _MIGRATION_0011_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # would raise AssertionError above if it tried

    assert hasattr(module, "upgrade")
    assert hasattr(module, "downgrade")
