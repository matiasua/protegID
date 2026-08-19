"""Smoke tests del Bloque 0: prueban la infraestructura de testing, no dominio.

No crear tests de ProtectedPerson aquí. Este archivo solo demuestra que:
- pytest está conectado inequívocamente a la DB de test;
- el aislamiento entre tests sobrevive a los session.commit() internos;
- la app FastAPI responde usando esa misma DB de test.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from app.repositories.users import create_user, get_user_by_email
from tests.conftest import NotATestDatabaseError, assert_safe_test_database

# Estos tres tests no se conectan a ninguna DB: validan el guard en sí mismo,
# antes de confiar en él para autorizar TRUNCATE/DROP sobre una DB real.


def test_assert_safe_test_database_accepts_test_database() -> None:
    assert_safe_test_database("postgresql://user:pass@localhost:5432/protegid_test")


def test_assert_safe_test_database_rejects_protegid() -> None:
    with pytest.raises(NotATestDatabaseError):
        assert_safe_test_database("postgresql://user:pass@localhost:5432/protegid")


def test_assert_safe_test_database_rejects_non_test_naming_policy() -> None:
    with pytest.raises(NotATestDatabaseError):
        assert_safe_test_database("postgresql://user:pass@localhost:5432/some_other_db")


def test_database_is_test_database(engine: Engine, test_database_url: str) -> None:
    expected_db_name = make_url(test_database_url).database
    assert expected_db_name is not None
    assert expected_db_name.endswith("_test")

    with engine.connect() as connection:
        actual_db_name = connection.execute(text("SELECT current_database()")).scalar_one()

    assert actual_db_name == expected_db_name


# Los dos tests siguientes dependen del orden de ejecución de pytest (top-down
# dentro del mismo archivo, comportamiento por defecto sin plugins de
# randomización). Se mantienen separados a propósito para demostrar que el
# aislamiento sobrevive entre invocaciones de test distintas, no solo dentro
# de un mismo test.


def test_database_cleanup_between_tests_step1_create(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        create_user(
            session,
            email="bloque0-isolation-check@example.com",
            password_hash="not-a-real-hash",
        )
    finally:
        session.close()


def test_database_cleanup_between_tests_step2_verify_gone(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = get_user_by_email(session, "bloque0-isolation-check@example.com")
    finally:
        session.close()

    assert user is None, (
        "El usuario creado (con commit()) en el test anterior sigue presente: "
        "la limpieza entre tests no está funcionando."
    )


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
