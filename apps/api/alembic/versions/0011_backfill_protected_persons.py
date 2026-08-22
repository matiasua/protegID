"""Backfill ProtectedPerson bridge from legacy Device/EmergencyProfile data.

Migration bridge (Bloque 3): populates ProtectedPerson + the protected_person_id
associations on Device/EmergencyProfile from existing legacy ownership data, and
makes emergency_profiles.device_id nullable so a future account-scoped profile
can exist without a Device. It does NOT switch any productive caller to the new
model: repositories/services/API still resolve exclusively through
Device.id -> EmergencyProfile.device_id after this migration runs.

SELF-CONTAINED BY DESIGN: this file deliberately does NOT import app.models or
any app.services module. Historical migrations must keep behaving the same way
even after the productive ORM models/services they were inspired by have
evolved or been deleted. Table/column shapes referenced below are a frozen
snapshot of the schema as it existed at 0010_add_protected_persons - if that
schema changes later, later migrations own the schema evolution; this file's
snapshot should not be "fixed" retroactively. The comparison/normalization
logic below is intentionally duplicated (not imported) from
app/services/protected_person_preflight.py for the same reason: that service
is free to evolve, this migration is not.

Revision ID: 0011_backfill_protected_persons
Revises: 0010_add_protected_persons
Create Date: 2026-08-19 00:00:00.000000
"""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op
from sqlalchemy import Boolean, DateTime, String, Text, column, func, select, table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


revision: str = "0011_backfill_protected_persons"
down_revision: str | None = "0010_add_protected_persons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --- Frozen local table shapes (schema as of 0010_add_protected_persons) ---
# Deliberately NOT the app.models declarative classes: those evolve, this
# migration must not.

devices_t = table(
    "devices",
    column("id", PG_UUID(as_uuid=True)),
    column("user_id", PG_UUID(as_uuid=True)),
    column("protected_person_id", PG_UUID(as_uuid=True)),
    column("public_id", String),
    column("deleted_at", DateTime(timezone=True)),
)

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
    column("deleted_at", DateTime(timezone=True)),
)

protected_persons_t = table(
    "protected_persons",
    column("id", PG_UUID(as_uuid=True)),
    column("account_user_id", PG_UUID(as_uuid=True)),
)


# --- Frozen canonical-content comparison (mirrors, does not import,
#     app/services/protected_person_preflight.py) ---

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

    devices = bind.execute(select(devices_t)).mappings().all()
    profiles = bind.execute(select(emergency_profiles_t)).mappings().all()
    devices_by_id = {d["id"]: d for d in devices}

    # --- Fail-fast divergence check: ACTIVE (non-soft-deleted) profiles
    #     only. A soft-deleted profile never counts as a competing "current"
    #     value for a user, so it never blocks the migration. ---
    active_profiles_by_user: dict = {}
    for profile in profiles:
        if profile["deleted_at"] is not None:
            continue
        device = devices_by_id.get(profile["device_id"])
        if device is None or device["user_id"] is None:
            continue
        active_profiles_by_user.setdefault(device["user_id"], []).append((device, profile))

    divergences = []
    for user_id, entries in active_profiles_by_user.items():
        if len(entries) < 2:
            continue
        _first_device, first_profile = entries[0]
        divergent_fields: set[str] = set()
        for _device, profile in entries[1:]:
            divergent_fields.update(_diff_fields(first_profile, profile))
        if divergent_fields:
            divergences.append(
                (
                    user_id,
                    tuple(d["public_id"] for d, _p in entries),
                    tuple(sorted(divergent_fields)),
                )
            )

    if divergences:
        summary = "; ".join(
            f"user={uid} devices={pubs} fields={fields}" for uid, pubs, fields in divergences
        )
        raise RuntimeError(
            "0011_backfill_protected_persons: divergent EmergencyProfile content "
            f"detected for {len(divergences)} user(s), aborting backfill without "
            f"writing anything: {summary}"
        )

    # --- A. One ProtectedPerson per User that owns at least one Device ---
    users_needing_protected_person = {
        d["user_id"] for d in devices if d["user_id"] is not None
    }

    existing_by_user = {
        row["account_user_id"]: row["id"]
        for row in bind.execute(select(protected_persons_t)).mappings().all()
    }

    pp_by_user = dict(existing_by_user)
    for user_id in users_needing_protected_person:
        if user_id in pp_by_user:
            continue
        new_id = uuid4()
        bind.execute(protected_persons_t.insert().values(id=new_id, account_user_id=user_id))
        pp_by_user[user_id] = new_id

    # --- B. Device.protected_person_id, regardless of status
    #         (active/lost/disabled all still represent the same identifier) ---
    for device in devices:
        if device["user_id"] is None or device["protected_person_id"] is not None:
            continue
        bind.execute(
            devices_t.update()
            .where(devices_t.c.id == device["id"])
            .values(protected_person_id=pp_by_user[device["user_id"]])
        )

    # --- C. EmergencyProfile.protected_person_id: RELATIONAL BACKFILL.
    #
    #     Scope is deliberately wider than the divergence check above:
    #     - ACTIVE profiles participate (divergence among them was already
    #       ruled out).
    #     - SOFT-DELETED profiles ALSO get backfilled here, as long as their
    #       own device_id -> Device.user_id -> ProtectedPerson chain is
    #       unambiguously determinable. Soft-delete means the row still
    #       exists historically; we know exactly which ProtectedPerson it
    #       belonged to, so we don't leave that FK unset just because the
    #       row happened to be soft-deleted during this bridge. This keeps
    #       a future `emergency_profiles.protected_person_id NOT NULL`
    #       reachable without artificial soft-delete exceptions.
    #     - A profile whose ownership cannot be determined (device missing,
    #       or device has no user_id) is left untouched and reported below
    #       as an anomaly - never guessed. ---
    undetermined_profile_ids = []
    for profile in profiles:
        if profile["protected_person_id"] is not None:
            continue
        device = devices_by_id.get(profile["device_id"])
        if device is None or device["user_id"] is None:
            undetermined_profile_ids.append(profile["id"])
            continue
        bind.execute(
            emergency_profiles_t.update()
            .where(emergency_profiles_t.c.id == profile["id"])
            .values(protected_person_id=pp_by_user[device["user_id"]])
        )

    if undetermined_profile_ids:
        print(
            "0011_backfill_protected_persons: "
            f"{len(undetermined_profile_ids)} emergency_profiles row(s) left without "
            "protected_person_id - ownership not determinable (orphan device or "
            f"missing device): ids={undetermined_profile_ids}"
        )

    # --- D. emergency_profiles.device_id becomes nullable, without dropping
    #         it: required so a future account-scoped profile can exist
    #         without a Device. Legacy repositories keep resolving via
    #         device_id unchanged. ---
    op.alter_column(
        "emergency_profiles",
        "device_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Only productive code in this bridge is *reading* through device_id;
    # nothing in this block creates account-scoped profiles yet, so no row
    # should have device_id IS NULL. Refuse to restore NOT NULL if that
    # assumption doesn't hold: that would mean account-scoped profiles
    # already exist under the C-lite model, and restoring the constraint
    # would corrupt them. We will not invent a Device, delete the profile,
    # or assign an arbitrary device_id to make the constraint pass.
    null_device_id_count = bind.execute(
        select(func.count())
        .select_from(emergency_profiles_t)
        .where(emergency_profiles_t.c.device_id.is_(None))
    ).scalar_one()

    if null_device_id_count:
        raise RuntimeError(
            "Cannot downgrade 0011_backfill_protected_persons: "
            f"{null_device_id_count} emergency_profiles row(s) have device_id "
            "IS NULL, meaning account-scoped profiles already exist under the "
            "C-lite model. Restoring the NOT NULL constraint would corrupt "
            "them. Downgrade refused."
        )

    op.alter_column(
        "emergency_profiles",
        "device_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=False,
    )

    # Remove only the associations this migration generated. protected_persons
    # ROWS are deliberately NOT deleted: the protected_persons TABLE already
    # existed at 0010 and stays owned by 0010's downgrade, not this one.
    # Keeping the rows preserves historical/diagnostic data and avoids this
    # downgrade silently destroying a ProtectedPerson that might be relied on
    # elsewhere by the time someone runs it.
    bind.execute(emergency_profiles_t.update().values(protected_person_id=None))
    bind.execute(devices_t.update().values(protected_person_id=None))
