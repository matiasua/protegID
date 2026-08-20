"""Repositorio de ProtectedPerson."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProtectedPerson


def get_by_id(session: Session, protected_person_id: UUID) -> ProtectedPerson | None:
    return session.get(ProtectedPerson, protected_person_id)


def get_by_account_user_id(
    session: Session, account_user_id: UUID
) -> ProtectedPerson | None:
    """Lectura cruda: devuelve la fila exista o no soft-deleted.

    account_user_id es UNIQUE independientemente de deleted_at, así que a lo
    sumo hay una fila por usuario. Distinguir "no existe" de "existe pero
    soft-deleted" es responsabilidad del caller (service), no de este repo.
    """
    statement = select(ProtectedPerson).where(
        ProtectedPerson.account_user_id == account_user_id
    )
    return session.scalar(statement)


def create_protected_person(
    session: Session, *, account_user_id: UUID
) -> ProtectedPerson:
    protected_person = ProtectedPerson(account_user_id=account_user_id)
    session.add(protected_person)
    return protected_person
