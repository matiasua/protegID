"""Add device claim security fields.

Revision ID: 0005_device_claim_fields
Revises: 0004_emergency_profiles
Create Date: 2026-05-24 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_device_claim_fields"
down_revision: str | None = "0004_emergency_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("claim_code_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "devices",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "devices",
        sa.Column("claim_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "devices",
        sa.Column("claim_locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("devices", "claim_locked_until")
    op.drop_column("devices", "claim_attempts")
    op.drop_column("devices", "claimed_at")
    op.drop_column("devices", "claim_code_hash")
