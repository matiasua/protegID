"""Add email verification fields and auth action tokens.

Revision ID: 0008_email_verification_tokens
Revises: 0007_create_auth_sessions_table
Create Date: 2026-05-27 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_email_verification_tokens"
down_revision: str | None = "0007_create_auth_sessions_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verification_sent_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_index(
        op.f("ix_users_email_verified_at"), "users", ["email_verified_at"], unique=False
    )

    op.create_table(
        "auth_action_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("sent_to_email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_action_tokens_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_action_tokens")),
    )
    op.create_index(
        op.f("ix_auth_action_tokens_user_id"),
        "auth_action_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auth_action_tokens_purpose"),
        "auth_action_tokens",
        ["purpose"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auth_action_tokens_token_hash"),
        "auth_action_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_auth_action_tokens_expires_at"),
        "auth_action_tokens",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auth_action_tokens_used_at"),
        "auth_action_tokens",
        ["used_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auth_action_tokens_revoked_at"),
        "auth_action_tokens",
        ["revoked_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auth_action_tokens_user_id_purpose"),
        "auth_action_tokens",
        ["user_id", "purpose"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_auth_action_tokens_user_id_purpose"),
        table_name="auth_action_tokens",
    )
    op.drop_index(op.f("ix_auth_action_tokens_revoked_at"), table_name="auth_action_tokens")
    op.drop_index(op.f("ix_auth_action_tokens_used_at"), table_name="auth_action_tokens")
    op.drop_index(op.f("ix_auth_action_tokens_expires_at"), table_name="auth_action_tokens")
    op.drop_index(op.f("ix_auth_action_tokens_token_hash"), table_name="auth_action_tokens")
    op.drop_index(op.f("ix_auth_action_tokens_purpose"), table_name="auth_action_tokens")
    op.drop_index(op.f("ix_auth_action_tokens_user_id"), table_name="auth_action_tokens")
    op.drop_table("auth_action_tokens")

    op.drop_index(op.f("ix_users_email_verified_at"), table_name="users")
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verified_at")
