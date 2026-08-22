"""Servicio productivo de ProtectedPerson (Bloque 4 — functional switch).

get_protected_person_for_user es de SOLO LECTURA: nunca crea, nunca restaura
una fila soft-deleted. get_or_create_protected_person puede crear, es
idempotente respecto de la UNIQUE(account_user_id), y jamás resucita un
ProtectedPerson soft-deleted: si encuentra uno, falla con un error de
dominio explícito en lugar de crear un duplicado o limpiar deleted_at.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ProtectedPerson, User
from app.repositories.protected_persons import get_by_account_user_id


class ProtectedPersonSoftDeletedError(RuntimeError):
    """Existe un ProtectedPerson para este usuario, pero está soft-deleted.

    Nunca se restaura ni se crea uno nuevo automáticamente: requiere una
    decisión explícita fuera de este flujo.
    """


def get_protected_person_for_user(
    session: Session, user: User
) -> ProtectedPerson | None:
    """Solo lectura. Nunca crea. Nunca filtra soft-deleted por sí mismo.

    Devuelve None si no existe ninguna fila. Si existe pero está
    soft-deleted, la devuelve igual: el caller decide cómo tratar ese caso
    (p. ej. GET account profile debe tratarlo como recurso no disponible,
    no como "perfil incompleto").
    """
    return get_by_account_user_id(session, user.id)


def get_or_create_protected_person(
    session: Session, user: User, *, commit: bool = True
) -> ProtectedPerson:
    """Idempotente respecto de UNIQUE(account_user_id). Maneja carrera
    concurrente: si dos requests intentan crear al mismo tiempo, uno gana el
    INSERT y el otro recupera esa misma fila tras el IntegrityError.

    El intento de INSERT se hace dentro de un SAVEPOINT
    (session.begin_nested()), no de la transacción completa: si otro proceso
    ganó la carrera, solo se deshace ese SAVEPOINT. Esta función se invoca
    desde dentro de PUT EmergencyProfile y Device activation, ambos flujos
    que pueden tener mutaciones pendientes en la misma sesión antes de
    llegar acá; un session.rollback() global las destruiría, así que nunca se
    usa aquí.

    IMPORTANTE: session.begin_nested() hace un flush automático de CUALQUIER
    objeto ya pendiente en la sesión al tomar su snapshot, antes de que el
    SAVEPOINT quede establecido. Por eso el session.add() del ProtectedPerson
    nuevo se hace DESPUÉS de entrar al bloque `with`, no antes: si se hiciera
    antes, ese INSERT escaparía del SAVEPOINT (se aplicaría durante el propio
    begin_nested()) y un IntegrityError lo dejaría fuera del alcance del
    except, dejando la sesión en estado no utilizable sin un rollback global.

    commit=False permite integrar la creación en una transacción más amplia
    donde el caller hace el único commit final. En ese modo el SAVEPOINT
    igual se usa para el intento de INSERT (vía flush), pero no hay commit()
    propio de esta función.
    """
    existing = get_by_account_user_id(session, user.id)
    if existing is not None:
        if existing.deleted_at is not None:
            raise ProtectedPersonSoftDeletedError(
                "ProtectedPerson exists but is soft-deleted for this account."
            )
        return existing

    protected_person = ProtectedPerson(account_user_id=user.id)
    try:
        with session.begin_nested():
            session.add(protected_person)
            session.flush()
    except IntegrityError:
        if protected_person in session:
            session.expunge(protected_person)
        existing = get_by_account_user_id(session, user.id)
        if existing is None:
            raise
        if existing.deleted_at is not None:
            raise ProtectedPersonSoftDeletedError(
                "ProtectedPerson exists but is soft-deleted for this account."
            ) from None
        return existing

    if commit:
        session.commit()
        session.refresh(protected_person)
    return protected_person
