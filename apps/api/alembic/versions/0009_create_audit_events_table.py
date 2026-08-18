"""Create audit events table.

Revision ID: 0009_audit_events
Revises: 0008_email_verification_tokens
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_audit_events"
down_revision: str | None = "0008_email_verification_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("public_id", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('success', 'failure')",
            name=op.f("ck_audit_events_outcome"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        op.f("ix_audit_events_created_at"),
        "audit_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_event_type_created_at"),
        "audit_events",
        ["event_type", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_actor_user_id_created_at"),
        "audit_events",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_target_user_id_created_at"),
        "audit_events",
        ["target_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_device_id_created_at"),
        "audit_events",
        ["device_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_public_id_created_at"),
        "audit_events",
        ["public_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_outcome_created_at"),
        "audit_events",
        ["outcome", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_request_id"),
        "audit_events",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_request_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_outcome_created_at"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_public_id_created_at"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_device_id_created_at"), table_name="audit_events")
    op.drop_index(
        op.f("ix_audit_events_target_user_id_created_at"), table_name="audit_events"
    )
    op.drop_index(
        op.f("ix_audit_events_actor_user_id_created_at"), table_name="audit_events"
    )
    op.drop_index(op.f("ix_audit_events_event_type_created_at"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_created_at"), table_name="audit_events")
    op.drop_table("audit_events")
