"""Bloque 8.4 — concurrencia de put_account_profile al crear el primer
EmergencyProfile de un ProtectedPerson.

Dos PUT concurrentes pueden ambos observar "sin perfil activo" (0 filas) y
ambos intentar el INSERT. uq_emergency_profiles_active_protected_person es la
última defensa, pero put_account_profile debe manejar el IntegrityError
resultante dentro de un SAVEPOINT (igual que
app.services.protected_persons.get_or_create_protected_person) y convertir al
perdedor en un UPDATE sobre la fila que ganó, sin propagar IntegrityError.
"""

import threading
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import EmergencyProfile, User
from app.repositories.users import create_user
from app.schemas.emergency_profile import EmergencyProfileCreate
from app.services.emergency_profiles import put_account_profile
from tests.helpers import ready_profile_payload


def _create_user(session) -> User:
    return create_user(
        session, email=f"{uuid4().hex}@example.com", password_hash="not-a-real-hash"
    )


def test_second_active_profile_for_same_protected_person_violates_unique_index(
    session_factory: sessionmaker,
) -> None:
    """Cobertura directa del partial unique index a HEAD: un segundo
    EmergencyProfile activo para el mismo ProtectedPerson debe fallar a nivel
    de constraint, no solo a nivel de servicio."""
    from sqlalchemy.exc import IntegrityError

    from app.services.protected_persons import get_or_create_protected_person
    from tests.helpers import make_active_profile

    session = session_factory()
    try:
        user = _create_user(session)
        protected_person = get_or_create_protected_person(session, user)
        make_active_profile(session, protected_person_id=protected_person.id)

        second = EmergencyProfile(
            protected_person_id=protected_person.id, **ready_profile_payload()
        )
        session.add(second)
        try:
            session.commit()
            assert False, "expected IntegrityError from the partial unique index"
        except IntegrityError:
            session.rollback()
    finally:
        session.close()


def test_real_concurrent_create_does_not_raise_unhandled_integrity_error(
    session_factory: sessionmaker,
) -> None:
    """Dos threads con sesiones propias hacen PUT /api/emergency-profile (vía
    servicio) para el mismo user al mismo tiempo, sin perfil previo. Solo uno
    gana el INSERT; el otro debe converger a la misma fila (actualizada) sin
    propagar IntegrityError."""
    setup_session = session_factory()
    try:
        user = _create_user(setup_session)
        user_id = user.id
    finally:
        setup_session.close()

    barrier = threading.Barrier(2)
    results: dict[str, EmergencyProfile] = {}
    errors: dict[str, BaseException] = {}

    def _attempt(key: str) -> None:
        session = session_factory()
        try:
            local_user = session.get(User, user_id)
            payload = EmergencyProfileCreate(**ready_profile_payload())
            barrier.wait(timeout=5)
            try:
                results[key] = put_account_profile(session, local_user, payload)
            except BaseException as exc:  # noqa: BLE001 - assertion en el hilo principal
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
                select(EmergencyProfile).where(
                    EmergencyProfile.protected_person_id
                    == results["a"].protected_person_id,
                    EmergencyProfile.deleted_at.is_(None),
                )
            )
        )
        assert len(rows) == 1
    finally:
        verify_session.close()
