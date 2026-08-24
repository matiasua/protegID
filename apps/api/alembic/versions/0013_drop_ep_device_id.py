"""Drop the legacy Device association from EmergencyProfile (Bloque 8.6 /
DB CONTRACT).

Retires `emergency_profiles.device_id` entirely: its FK to devices.id, its
UNIQUE constraint, and the column itself. This is the last remnant of the
pre-ProtectedPerson data model (Device -> EmergencyProfile, one profile per
device). The productive relationship going forward is exclusively:

    User -> ProtectedPerson -> EmergencyProfile
    Device -> ProtectedPerson

0011 already made device_id nullable (to allow account-scoped profiles with
no Device) and 0012 already made protected_person_id NOT NULL with a partial
unique index enforcing at most one ACTIVE profile per ProtectedPerson. By the
time this migration runs, protected_person_id is the sole productive
ownership path; device_id has had 0 productive runtime readers/writers since
Bloque 8.4 (canonical/shadow simplification) and 0 remaining callers at all
as of Bloque 8.6's audit (see docs/ai-rules.md).

Preflight (informational only, does not block): reports how many rows still
carry a non-NULL device_id, purely as a count - never row-level data - so an
operator running this against a real DB has a sense of how much legacy
association is being discarded. Never blocks the DROP: this column is being
retired deliberately, and any historical device_id value is by definition
legacy data this migration is designed to discard.

SELF-CONTAINED BY DESIGN, same rationale as 0011/0012: this file does NOT
import app.models or app.services. The table/constraint shapes below are a
frozen snapshot as of 0012_consolidate_active_ep; they are intentionally
duplicated (not imported) from app/models/emergency_profile.py so this
migration's behavior never changes when that productive code evolves.

Downgrade: restores the column/FK/UNIQUE structurally (device_id UUID NULL,
FK to devices.id, UNIQUE(device_id)) exactly as 0012 left it - but leaves
every restored value NULL. It does NOT reconstruct which EmergencyProfile
used to be associated with which Device: that association is destroyed by
the upgrade and cannot be un-destroyed, because a ProtectedPerson can have
multiple Devices (see Device.protected_person_id) and there is no
deterministic, safe way to pick "the" Device a downgrade should re-associate
a profile with. Picking first/oldest/newest Device would be inventing data,
not restoring it. 0012 already nullable-allowed exactly this: device_id was
NULL-safe by design once account-scoped profiles existed.

Revision ID: 0013_drop_ep_device_id
Revises: 0012_consolidate_active_ep
Create Date: 2026-08-22 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import Column, column, func, select, table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0013_drop_ep_device_id"
down_revision: str | None = "0012_consolidate_active_ep"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_FK_NAME = "fk_emergency_profiles_device_id_devices"
_UNIQUE_NAME = "uq_emergency_profiles_device_id"

# --- Frozen local table shape (schema as of 0012_consolidate_active_ep) ---
# Deliberately NOT the app.models declarative class: that evolves, this
# migration must not.

emergency_profiles_t = table(
    "emergency_profiles",
    column("device_id", PG_UUID(as_uuid=True)),
)


def upgrade() -> None:
    bind = op.get_bind()

    # Informational only: never blocks the DROP. Reports a count, never row
    # content or ids, so it stays safe to run against a real DB.
    legacy_device_id_count = bind.execute(
        select(func.count())
        .select_from(emergency_profiles_t)
        .where(emergency_profiles_t.c.device_id.isnot(None))
    ).scalar_one()
    if legacy_device_id_count:
        print(
            "0013_drop_ep_device_id: discarding legacy device_id association "
            f"for {legacy_device_id_count} emergency_profiles row(s). This is "
            "expected and deliberate: protected_person_id is the sole "
            "productive ownership path as of this migration."
        )

    op.drop_constraint(_UNIQUE_NAME, "emergency_profiles", type_="unique")
    op.drop_constraint(_FK_NAME, "emergency_profiles", type_="foreignkey")
    op.drop_column("emergency_profiles", "device_id")


def downgrade() -> None:
    # Structural restore only - see module docstring for why values are NOT
    # reconstructed: a ProtectedPerson can have multiple Devices, and picking
    # one automatically would invent an association, not restore it.
    op.add_column(
        "emergency_profiles",
        Column("device_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        _FK_NAME,
        "emergency_profiles",
        "devices",
        ["device_id"],
        ["id"],
    )
    op.create_unique_constraint(_UNIQUE_NAME, "emergency_profiles", ["device_id"])
