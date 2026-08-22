"""Add protected_persons table (C-lite schema foundation, expand-only).

Revision ID: 0010_add_protected_persons
Revises: 0009_audit_events
Create Date: 2026-08-19 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0010_add_protected_persons"
down_revision: str | None = "0009_audit_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "protected_persons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_user_id"],
            ["users.id"],
            name=op.f("fk_protected_persons_account_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_protected_persons")),
        sa.UniqueConstraint(
            "account_user_id", name=op.f("uq_protected_persons_account_user_id")
        ),
    )

    op.add_column(
        "devices",
        sa.Column("protected_person_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_devices_protected_person_id"),
        "devices",
        ["protected_person_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_devices_protected_person_id_protected_persons"),
        "devices",
        "protected_persons",
        ["protected_person_id"],
        ["id"],
    )

    op.add_column(
        "emergency_profiles",
        sa.Column("protected_person_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_emergency_profiles_protected_person_id"),
        "emergency_profiles",
        ["protected_person_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_emergency_profiles_protected_person_id_protected_persons"),
        "emergency_profiles",
        "protected_persons",
        ["protected_person_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_emergency_profiles_protected_person_id_protected_persons"),
        "emergency_profiles",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_emergency_profiles_protected_person_id"),
        table_name="emergency_profiles",
    )
    op.drop_column("emergency_profiles", "protected_person_id")

    op.drop_constraint(
        op.f("fk_devices_protected_person_id_protected_persons"),
        "devices",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_devices_protected_person_id"), table_name="devices")
    op.drop_column("devices", "protected_person_id")

    op.drop_table("protected_persons")
