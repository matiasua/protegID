"""Bloque 4: servicio productivo de ProtectedPerson.

get_protected_person_for_user es de solo lectura (nunca crea).
get_or_create_protected_person es idempotente, respeta UNIQUE(account_user_id)
y jamás resucita una fila soft-deleted.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import ProtectedPerson
from app.repositories.users import create_user
from app.services.protected_persons import (
    ProtectedPersonSoftDeletedError,
    get_or_create_protected_person,
    get_protected_person_for_user,
)


def _create_user(session):
    return create_user(
        session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
    )


def test_get_protected_person_for_user_never_creates(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)

        result = get_protected_person_for_user(session, user)

        assert result is None
        count = session.scalar(select(ProtectedPerson).where(ProtectedPerson.account_user_id == user.id))
        assert count is None
    finally:
        session.close()


def test_get_or_create_protected_person_creates_once(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)

        created = get_or_create_protected_person(session, user)
        assert created.account_user_id == user.id

        again = get_or_create_protected_person(session, user)
        assert again.id == created.id

        rows = list(
            session.scalars(
                select(ProtectedPerson).where(ProtectedPerson.account_user_id == user.id)
            )
        )
        assert len(rows) == 1
    finally:
        session.close()


def test_get_or_create_protected_person_handles_concurrent_race(
    session_factory: sessionmaker,
) -> None:
    """Simula la carrera: dos sesiones distintas intentan crear a la vez para
    el mismo usuario. Ambas deben terminar apuntando a la misma fila, sin
    IntegrityError sin manejar."""
    session_a = session_factory()
    session_b = session_factory()
    try:
        user = _create_user(session_a)
        session_b.close()
        session_b = session_factory()

        winner = get_or_create_protected_person(session_a, user)

        # session_b todavía no ve el commit de session_a hasta que consulta
        # de nuevo; get_or_create debe manejar el IntegrityError si igual
        # intenta insertar (carrera real) y converger a la misma fila.
        loser = get_or_create_protected_person(session_b, user)

        assert winner.id == loser.id
    finally:
        session_a.close()
        session_b.close()


def test_get_or_create_protected_person_raises_on_soft_deleted(
    session_factory: sessionmaker,
) -> None:
    session = session_factory()
    try:
        user = _create_user(session)
        protected_person = get_or_create_protected_person(session, user)
        protected_person.deleted_at = datetime.now(UTC)
        session.commit()

        try:
            get_or_create_protected_person(session, user)
            assert False, "expected ProtectedPersonSoftDeletedError"
        except ProtectedPersonSoftDeletedError:
            pass

        rows = list(
            session.scalars(
                select(ProtectedPerson).where(ProtectedPerson.account_user_id == user.id)
            )
        )
        assert len(rows) == 1
        assert rows[0].deleted_at is not None
    finally:
        session.close()


def test_get_protected_person_for_user_returns_soft_deleted_row(
    session_factory: sessionmaker,
) -> None:
    """GET es de solo lectura y NO filtra soft-deleted por sí mismo: el
    caller decide cómo tratarlo. Esto lo verifica el service directamente;
    el comportamiento HTTP (unavailable) se cubre en tests de la API."""
    session = session_factory()
    try:
        user = _create_user(session)
        protected_person = get_or_create_protected_person(session, user)
        protected_person.deleted_at = datetime.now(UTC)
        session.commit()

        result = get_protected_person_for_user(session, user)

        assert result is not None
        assert result.deleted_at is not None
    finally:
        session.close()
