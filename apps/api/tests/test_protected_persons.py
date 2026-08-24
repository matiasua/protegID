"""Bloque 1: schema foundation de ProtectedPerson (expand-only).

Solo prueba estructura (tabla, constraints, FKs, upgrade/downgrade). No hay
todavía repository/service de ProtectedPerson ni comportamiento funcional
C-lite: eso es Bloque 2+.
"""

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import Device, ProtectedPerson, User
from app.repositories.users import create_user
from tests.conftest import assert_safe_test_database

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _create_device(session, *, user_id) -> Device:
    device = Device(user_id=user_id, public_id=f"dev-{uuid4().hex}")
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def test_alembic_creates_protected_persons_table(engine: sa.Engine) -> None:
    inspector = sa.inspect(engine)
    assert "protected_persons" in inspector.get_table_names()

    columns = {c["name"] for c in inspector.get_columns("protected_persons")}
    assert {"id", "account_user_id", "created_at", "updated_at", "deleted_at"} <= columns


def test_account_user_id_is_unique(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )

        session.add(ProtectedPerson(account_user_id=user.id))
        session.commit()

        session.add(ProtectedPerson(account_user_id=user.id))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_device_can_exist_with_null_protected_person_id(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = _create_device(session, user_id=user.id)

        assert device.protected_person_id is None
    finally:
        session.close()


def test_invalid_protected_person_id_fk_is_rejected(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = create_user(
            session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        device = Device(
            user_id=user.id,
            public_id=f"dev-{uuid4().hex}",
            protected_person_id=uuid4(),  # no existe en protected_persons
        )
        session.add(device)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


@pytest.mark.migration
def test_downgrade_0010_removes_protected_person_schema_and_restores_head(
    engine: sa.Engine, test_database_url: str
) -> None:
    """Round-trip 0010 -> 0009 -> 0010. Debe dejar la DB en head al terminar,
    para no romper el resto de la suite ni el cleanup autouse."""
    assert_safe_test_database(test_database_url)

    cfg = Config(str(_ALEMBIC_INI))

    try:
        command.downgrade(cfg, "0009_audit_events")

        inspector = sa.inspect(engine)
        assert "protected_persons" not in inspector.get_table_names()

        device_columns = {c["name"] for c in inspector.get_columns("devices")}
        assert "protected_person_id" not in device_columns

        profile_columns = {c["name"] for c in inspector.get_columns("emergency_profiles")}
        assert "protected_person_id" not in profile_columns

        # Tablas preexistentes intactas.
        assert {"users", "devices", "emergency_profiles", "audit_events"} <= set(
            inspector.get_table_names()
        )
    finally:
        command.upgrade(cfg, "head")

    inspector = sa.inspect(engine)
    assert "protected_persons" in inspector.get_table_names()
    assert "protected_person_id" in {
        c["name"] for c in inspector.get_columns("devices")
    }
    assert "protected_person_id" in {
        c["name"] for c in inspector.get_columns("emergency_profiles")
    }
