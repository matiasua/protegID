"""Create emergency profiles table.

Revision ID: 0004_emergency_profiles
Revises: 0003_create_devices_table
Create Date: 2026-05-22 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_emergency_profiles"
down_revision: str | None = "0003_create_devices_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emergency_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("blood_type", sa.String(length=10), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("medical_conditions", sa.Text(), nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("emergency_contact_name", sa.String(length=255), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(length=50), nullable=True),
        sa.Column(
            "emergency_contact_relationship", sa.String(length=100), nullable=True
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default="true", nullable=False),
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
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_emergency_profiles_device_id_devices"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emergency_profiles")),
        sa.UniqueConstraint(
            "device_id", name=op.f("uq_emergency_profiles_device_id")
        ),
    )


def downgrade() -> None:
    op.drop_table("emergency_profiles")
