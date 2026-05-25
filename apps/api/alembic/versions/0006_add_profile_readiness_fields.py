"""Add profile readiness and consent fields.

Revision ID: 0006_profile_readiness_fields
Revises: 0005_device_claim_fields
Create Date: 2026-05-24 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_profile_readiness_fields"
down_revision: str | None = "0005_device_claim_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "emergency_profiles",
        sa.Column(
            "medical_conditions_none",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "emergency_profiles",
        sa.Column(
            "allergies_none",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "emergency_profiles",
        sa.Column(
            "medications_none",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "emergency_profiles",
        sa.Column(
            "public_consent_accepted_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "emergency_profiles",
        sa.Column("public_consent_version", sa.String(length=50), nullable=True),
    )
    op.alter_column(
        "emergency_profiles",
        "is_public",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.alter_column(
        "emergency_profiles",
        "is_public",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.text("true"),
    )
    op.drop_column("emergency_profiles", "public_consent_version")
    op.drop_column("emergency_profiles", "public_consent_accepted_at")
    op.drop_column("emergency_profiles", "medications_none")
    op.drop_column("emergency_profiles", "allergies_none")
    op.drop_column("emergency_profiles", "medical_conditions_none")
