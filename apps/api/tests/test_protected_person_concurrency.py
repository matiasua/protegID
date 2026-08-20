"""Bloque 4 — concurrencia de get_or_create_protected_person.

El INSERT se intenta dentro de un SAVEPOINT (session.begin_nested()), nunca
con un session.rollback() de la transacción completa: esta función se llama
desde dentro de PUT EmergencyProfile y Device activation, ambos con
mutaciones propias en la misma sesión que no deben perderse si otro proceso
gana la carrera de creación del ProtectedPerson.
"""

import threading
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import ProtectedPerson, User
from app.repositories.users import create_user
from app.services.protected_persons import get_or_create_protected_person


def _create_user(session) -> User:
    return create_user(
        session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
    )


def test_normal_call_creates_a_single_person(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)

        created = get_or_create_protected_person(session, user)

        rows = list(
            session.scalars(
                select(ProtectedPerson).where(
                    ProtectedPerson.account_user_id == user.id
                )
            )
        )
        assert len(rows) == 1
        assert rows[0].id == created.id
    finally:
        session.close()


def test_second_call_reuses_the_same_person(session_factory: sessionmaker) -> None:
    session = session_factory()
    try:
        user = _create_user(session)

        first = get_or_create_protected_person(session, user)
        second = get_or_create_protected_person(session, user)

        assert first.id == second.id
    finally:
        session.close()


def test_real_concurrent_race_does_not_raise_unhandled_integrity_error(
    session_factory: sessionmaker,
) -> None:
    """Dos threads con sesiones/conexiones propias intentan crear el
    ProtectedPerson del mismo user al mismo tiempo. Solo uno gana el INSERT;
    el otro debe converger a la misma fila sin propagar IntegrityError ni
    necesitar un rollback global de su propia transacción."""
    setup_session = session_factory()
    try:
        user = _create_user(setup_session)
        user_id = user.id
    finally:
        setup_session.close()

    barrier = threading.Barrier(2)
    results: dict[str, ProtectedPerson] = {}
    errors: dict[str, BaseException] = {}

    def _attempt(key: str) -> None:
        session = session_factory()
        try:
            local_user = session.get(User, user_id)
            barrier.wait(timeout=5)
            try:
                results[key] = get_or_create_protected_person(session, local_user)
            except BaseException as exc:  # noqa: BLE001 - capturamos para assertion en el hilo principal
                errors[key] = exc
        finally:
            session.close()

    thread_a = threading.Thread(target=_attempt, args=("a",))
    thread_b = threading.Thread(target=_attempt, args=("b",))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)

    assert not errors, f"unexpected errors from concurrent attempts: {errors}"
    assert results["a"].id == results["b"].id

    verify_session = session_factory()
    try:
        rows = list(
            verify_session.scalars(
                select(ProtectedPerson).where(
                    ProtectedPerson.account_user_id == user_id
                )
            )
        )
        assert len(rows) == 1
    finally:
        verify_session.close()


def test_pending_caller_mutation_survives_conflict_path(
    session_factory: sessionmaker, monkeypatch
) -> None:
    """Si el caller ya tiene una mutación pendiente (no comiteada) en la
    misma sesión antes de invocar get_or_create con commit=False, y el
    intento de INSERT choca contra una fila ya creada por otra sesión (carrera
    real: el SELECT inicial del caller no vio todavía esa fila), esa mutación
    pendiente debe sobrevivir: el SAVEPOINT solo deshace el INSERT fallido,
    nunca la transacción completa del caller."""
    import app.services.protected_persons as protected_persons_module

    winner_session = session_factory()
    try:
        user = _create_user(winner_session)
        winner = get_or_create_protected_person(winner_session, user)
    finally:
        winner_session.close()

    caller_session = session_factory()
    try:
        local_user = caller_session.get(User, user.id)

        pending_user = User(
            email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
        )
        caller_session.add(pending_user)

        # Simula la carrera real: el SELECT inicial de get_or_create no vio
        # todavía la fila ganadora (ya comiteada por otra sesión), así que
        # intenta el INSERT y choca con la UNIQUE constraint. La siguiente
        # llamada (dentro del manejo de conflicto) sí ve la fila real.
        real_get_by_account_user_id = protected_persons_module.get_by_account_user_id
        call_count = {"n": 0}

        def _stale_then_real(session, account_user_id):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return None
            return real_get_by_account_user_id(session, account_user_id)

        monkeypatch.setattr(
            protected_persons_module, "get_by_account_user_id", _stale_then_real
        )

        result = get_or_create_protected_person(caller_session, local_user, commit=False)
        assert result.id == winner.id
        assert call_count["n"] == 2  # confirma que sí pasó por el conflicto real

        caller_session.commit()

        assert pending_user.id is not None
        rows = list(
            caller_session.scalars(select(User).where(User.id == pending_user.id))
        )
        assert len(rows) == 1
    finally:
        caller_session.close()


def test_soft_deleted_continues_blocking_creation_after_conflict_handling(
    session_factory: sessionmaker,
) -> None:
    from datetime import UTC, datetime

    from app.services.protected_persons import ProtectedPersonSoftDeletedError

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
                select(ProtectedPerson).where(
                    ProtectedPerson.account_user_id == user.id
                )
            )
        )
        assert len(rows) == 1
        assert rows[0].deleted_at is not None
    finally:
        session.close()
