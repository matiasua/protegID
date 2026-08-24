"""Modelo de perfil de emergencia."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.protected_person import ProtectedPerson


class EmergencyProfile(Base):
    """máximo un EmergencyProfile ACTIVE (deleted_at IS NULL) por
    ProtectedPerson (ver uq_emergency_profiles_active_protected_person, un
    partial unique index, no una constraint plana: perfiles históricos
    soft-deleted pueden coexistir). Esa regla de dominio se resuelve vía
    repository/service (get_canonical_emergency_profile), nunca asumiendo que
    `protected_person.emergency_profiles` tiene un único elemento: la
    colección ORM incluye el historial soft-deleted a propósito."""

    __tablename__ = "emergency_profiles"
    __table_args__ = (
        Index(
            "uq_emergency_profiles_active_protected_person",
            "protected_person_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    protected_person_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("protected_persons.id"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    emergency_contact_phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    emergency_contact_relationship: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    medical_conditions_none: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    allergies_none: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    medications_none: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    public_consent_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    public_consent_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    protected_person: Mapped["ProtectedPerson"] = relationship(
        back_populates="emergency_profiles"
    )
