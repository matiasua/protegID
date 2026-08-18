"""Modelo de eventos de auditoría."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.db import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success', 'failure')",
            name="ck_audit_events_outcome",
        ),
        Index("ix_audit_events_event_type_created_at", "event_type", "created_at"),
        Index(
            "ix_audit_events_actor_user_id_created_at",
            "actor_user_id",
            "created_at",
        ),
        Index(
            "ix_audit_events_target_user_id_created_at",
            "target_user_id",
            "created_at",
        ),
        Index("ix_audit_events_device_id_created_at", "device_id", "created_at"),
        Index("ix_audit_events_public_id_created_at", "public_id", "created_at"),
        Index("ix_audit_events_outcome_created_at", "outcome", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    device_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    public_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
