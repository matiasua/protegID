"""Consolidate duplicate active EmergencyProfile rows and enforce the
single-active-profile-per-ProtectedPerson invariant (Bloque 5).

After 0011, a ProtectedPerson could transiently have more than one ACTIVE
(non-soft-deleted) EmergencyProfile: one per legacy Device that used to point
at equivalent profile content. This migration:

  1. Fails fast (writes nothing) if any emergency_profiles row still has
     protected_person_id IS NULL - that anomaly must be resolved upstream
     (0011 / preflight), never guessed here.
  2. Fails fast (writes nothing) if any ProtectedPerson has >1 ACTIVE profile
     whose domain content diverges - never selects, never merges, never
     deletes a divergent row automatically.
  3. For ProtectedPersons with >1 ACTIVE *equivalent* profiles, deterministically
     selects one canonical row (created_at ASC, id ASC - the same rule the
     transitional runtime resolver in app/services/emergency_profile_canonical.py
     uses) and soft-deletes (deleted_at = migration timestamp, never a hard
     DELETE) the rest as historical shadows.
  4. Makes emergency_profiles.protected_person_id NOT NULL.
  5. Adds a partial unique index enforcing at most one ACTIVE
     (deleted_at IS NULL) EmergencyProfile per protected_person_id. Not a
     plain UNIQUE(protected_person_id): historical soft-deleted profiles for
     the same ProtectedPerson must remain representable.

SELF-CONTAINED BY DESIGN, same rationale as 0011: this file does NOT import
app.models or app.services. The table shape and the canonical-content
comparison below are a frozen snapshot as of 0011_backfill_protected_persons;
they are intentionally duplicated (not imported) from
app/services/protected_person_preflight.py / app/services/emergency_profile_canonical.py
so this migration's behavior never changes when that productive code evolves.

Revision ID: 0012_consolidate_active_ep
Revises: 0011_backfill_protected_persons
Create Date: 2026-08-20 00:00:00.000000

Named "active_ep" (not the fuller "consolidate_emergency_profiles") only to
fit alembic_version.version_num (varchar(32)); no shorthand is used in
identifiers or docs elsewhere in this file.
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Boolean, DateTime, String, Text, column, func, select, table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


revision: str = "0012_consolidate_active_ep"
down_revision: str | None = "0011_backfill_protected_persons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ACTIVE_UNIQUE_INDEX_NAME = "uq_emergency_profiles_active_protected_person"


# --- Frozen local table shape (schema as of 0011_backfill_protected_persons) ---
# Deliberately NOT the app.models declarative class: that evolves, this
# migration must not.

emergency_profiles_t = table(
    "emergency_profiles",
    column("id", PG_UUID(as_uuid=True)),
    column("device_id", PG_UUID(as_uuid=True)),
    column("protected_person_id", PG_UUID(as_uuid=True)),
    column("display_name", String),
    column("emergency_contact_name", String),
    column("emergency_contact_relationship", String),
    column("emergency_contact_phone", String),
    column("medical_conditions", Text),
    column("medical_conditions_none", Boolean),
    column("allergies", Text),
    column("allergies_none", Boolean),
    column("medications", Text),
    column("medications_none", Boolean),
    column("blood_type", String),
    column("notes", Text),
    column("is_public", Boolean),
    column("public_consent_accepted_at", DateTime(timezone=True)),
    column("public_consent_version", String),
    column("created_at", DateTime(timezone=True)),
    column("deleted_at", DateTime(timezone=True)),
)


# --- Frozen canonical-content comparison (mirrors, does not import,
#     app/services/protected_person_preflight.py / emergency_profile_canonical.py) ---

_CANONICAL_TEXT_FIELDS = (
    "display_name",
    "emergency_contact_name",
    "emergency_contact_relationship",
    "emergency_contact_phone",
    "medical_conditions",
    "allergies",
    "medications",
    "blood_type",
    "notes",
    "public_consent_version",
)
_CANONICAL_BOOL_FIELDS = (
    "medical_conditions_none",
    "allergies_none",
    "medications_none",
    "is_public",
)
_CANONICAL_DATETIME_FIELDS = ("public_consent_accepted_at",)


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped != "" else None


def _diff_fields(a, b) -> list[str]:
    diffs = [f for f in _CANONICAL_TEXT_FIELDS if _normalize_text(a[f]) != _normalize_text(b[f])]
    diffs += [f for f in _CANONICAL_BOOL_FIELDS if bool(a[f]) != bool(b[f])]
    diffs += [f for f in _CANONICAL_DATETIME_FIELDS if a[f] != b[f]]
    return diffs


def upgrade() -> None:
    bind = op.get_bind()

    # --- Precondition A: no emergency_profiles row may have
    #     protected_person_id IS NULL. 0011 already backfilled every row it
    #     could determine ownership for; a NULL here is an anomaly that must
    #     be investigated upstream, not invented or repaired in 0012. ---
    null_owner_count = bind.execute(
        select(func.count())
        .select_from(emergency_profiles_t)
        .where(emergency_profiles_t.c.protected_person_id.is_(None))
    ).scalar_one()

    if null_owner_count:
        raise RuntimeError(
            "0012_consolidate_emergency_profiles: "
            f"{null_owner_count} emergency_profiles row(s) have protected_person_id "
            "IS NULL. Refusing to run: this must be resolved (0011/preflight "
            "review), never guessed by this migration. Aborting without writing "
            "anything."
        )

    # --- Group ACTIVE (non-soft-deleted) profiles by protected_person_id.
    #     Soft-deleted profiles never participate in selection or divergence
    #     checks - they are historical and are left untouched. ---
    active_profiles = (
        bind.execute(
            select(emergency_profiles_t).where(emergency_profiles_t.c.deleted_at.is_(None))
        )
        .mappings()
        .all()
    )

    active_by_person: dict = {}
    for profile in active_profiles:
        active_by_person.setdefault(profile["protected_person_id"], []).append(profile)

    # --- Precondition B/C: re-verify equivalence across ALL groups before
    #     touching anything. Fail fast (no partial writes) if any group of
    #     >1 active profiles diverges. ---
    divergences = []
    consolidation_groups: list[tuple] = []  # (protected_person_id, [profiles])

    for protected_person_id, entries in active_by_person.items():
        if len(entries) < 2:
            continue

        first = entries[0]
        divergent_fields: set[str] = set()
        for other in entries[1:]:
            divergent_fields.update(_diff_fields(first, other))

        if divergent_fields:
            divergences.append(
                (
                    protected_person_id,
                    tuple(sorted(str(p["id"]) for p in entries)),
                    tuple(sorted(divergent_fields)),
                )
            )
        else:
            consolidation_groups.append((protected_person_id, entries))

    if divergences:
        summary = "; ".join(
            f"protected_person_id={pp} profiles={ids} fields={fields}"
            for pp, ids, fields in divergences
        )
        raise RuntimeError(
            "0012_consolidate_emergency_profiles: divergent ACTIVE EmergencyProfile "
            f"content detected for {len(divergences)} protected person(s), aborting "
            f"without writing anything: {summary}"
        )

    # --- Consolidate equivalent duplicates: deterministic canonical
    #     selection (created_at ASC, id ASC - same rule as the transitional
    #     runtime resolver), soft-delete the rest. Never a hard DELETE: the
    #     shadows become ordinary historical soft-deleted rows. A single
    #     consolidation timestamp is used for every shadow soft-deleted by
    #     this migration run, for reproducibility/auditability. ---
    consolidation_timestamp: datetime = bind.execute(select(func.now())).scalar_one()

    for _protected_person_id, entries in consolidation_groups:
        ordered = sorted(entries, key=lambda p: (p["created_at"], str(p["id"])))
        shadows = ordered[1:]
        shadow_ids = [shadow["id"] for shadow in shadows]
        bind.execute(
            emergency_profiles_t.update()
            .where(emergency_profiles_t.c.id.in_(shadow_ids))
            .values(deleted_at=consolidation_timestamp)
        )

    # --- protected_person_id becomes NOT NULL: precondition A already
    #     guaranteed 0 NULLs before any write in this migration ran. ---
    op.alter_column(
        "emergency_profiles",
        "protected_person_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=False,
    )

    # --- Partial unique index: at most one ACTIVE EmergencyProfile per
    #     ProtectedPerson. Deliberately NOT a plain UNIQUE(protected_person_id):
    #     that would forbid the historical soft-deleted rows we just
    #     preserved (and any pre-existing ones). ---
    op.create_index(
        _ACTIVE_UNIQUE_INDEX_NAME,
        "emergency_profiles",
        ["protected_person_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(_ACTIVE_UNIQUE_INDEX_NAME, table_name="emergency_profiles")

    op.alter_column(
        "emergency_profiles",
        "protected_person_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Deliberately NOT reversed: the shadow rows this migration soft-deleted
    # during consolidation stay soft-deleted. Un-soft-deleting them would mean
    # inventing which of several equivalent historical profiles should become
    # ACTIVE again - a clinical/ownership decision this migration has no basis
    # to make. The rows themselves were never destroyed (soft-delete, not
    # DELETE), so no data is lost; only the "was this one specifically
    # consolidated by 0012" fact is not automatically undone. Consolidating
    # active duplicates is therefore a non-semantically-reversible data
    # transformation by design.
