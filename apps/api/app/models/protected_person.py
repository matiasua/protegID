"""Modelo de persona protegida (C-lite)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.emergency_profile import EmergencyProfile
    from app.models.user import User


class ProtectedPerson(Base):
    __tablename__ = "protected_persons"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    account_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account_user: Mapped["User"] = relationship(back_populates="protected_person")
    devices: Mapped[list["Device"]] = relationship(back_populates="protected_person")
    emergency_profiles: Mapped[list["EmergencyProfile"]] = relationship(
        back_populates="protected_person"
    )
