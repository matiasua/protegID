"""Preflight de solo lectura para el bridge de datos hacia ProtectedPerson (Bloque 3).

Inspecciona el estado actual (User/Device/EmergencyProfile) sin escribir nada, y
decide si el estado de datos es seguro para el backfill de la migración 0011.

Regla central: fail-fast. Si un mismo User tiene múltiples EmergencyProfile
activos (no soft-deleted) con contenido de dominio divergente, este módulo lo
reporta explícitamente. Nunca elige un perfil "ganador", nunca fusiona.

Este módulo es reutilizable: la migración 0011 lo invoca contra la conexión
del propio `op.get_bind()`, y también puede invocarse de forma independiente
(script, test, chequeo manual contra development) pasando cualquier bind
SQLAlchemy 2.0-style (`Session` o `Connection`) que soporte `.execute()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select

from app.models import Device, EmergencyProfile

# Campos que forman el contenido de DOMINIO de un EmergencyProfile: lo que
# realmente distingue "el mismo perfil" de "un perfil distinto". Deliberadamente
# excluidos de esta lista (no son contenido, son metadata de asociación/auditoría):
#   - id                    (identidad de fila, no de dominio)
#   - device_id             (asociación legacy, no contenido del perfil)
#   - protected_person_id   (asociación C-lite, no contenido del perfil)
#   - created_at / updated_at (metadata de auditoría)
# deleted_at se trata explícitamente por separado (ver `run_preflight`): un
# perfil soft-deleted NUNCA participa en la comparación de divergencia/
# equivalencia de un usuario. No se ignora en silencio: se cuenta aparte
# (`soft_deleted_profiles`) y se excluye a propósito de la agrupación por user.
CANONICAL_TEXT_FIELDS = (
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
CANONICAL_BOOL_FIELDS = (
    "medical_conditions_none",
    "allergies_none",
    "medications_none",
    "is_public",
)
CANONICAL_DATETIME_FIELDS = ("public_consent_accepted_at",)

CANONICAL_FIELDS: tuple[str, ...] = (
    CANONICAL_TEXT_FIELDS + CANONICAL_BOOL_FIELDS + CANONICAL_DATETIME_FIELDS
)


def _normalize_text(value: str | None) -> str | None:
    """None, "" y whitespace-only son la misma representación de "vacío".

    Esto es normalización de REPRESENTACIÓN, no de contenido médico: nunca
    recorta, reescribe, combina ni interpreta texto real. Un valor con
    contenido (aunque sea distinto) nunca se toca.
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped != "" else None


def _normalized_value(profile: EmergencyProfile, field_name: str) -> object:
    raw = getattr(profile, field_name)
    if field_name in CANONICAL_TEXT_FIELDS:
        return _normalize_text(raw)
    return raw


def canonical_profile_key(profile: EmergencyProfile) -> tuple:
    """Representación canónica del contenido de dominio de un perfil.

    Dos perfiles con la misma canonical_profile_key se consideran
    equivalentes a efectos de este bridge.
    """
    return tuple(_normalized_value(profile, f) for f in CANONICAL_FIELDS)


def diff_fields(a: EmergencyProfile, b: EmergencyProfile) -> list[str]:
    """Campos canónicos en los que `a` y `b` difieren (tras normalización)."""
    return [
        f
        for f in CANONICAL_FIELDS
        if _normalized_value(a, f) != _normalized_value(b, f)
    ]


def _safe_field_hash(profile: EmergencyProfile, field_name: str) -> str:
    """Resumen no reversible de un campo, para reportar divergencias sin
    imprimir contenido médico/PII completo."""
    normalized = _normalized_value(profile, field_name)
    digest_input = repr(normalized).encode("utf-8")
    return sha256(digest_input).hexdigest()[:12]


@dataclass(frozen=True)
class ProfileDivergence:
    user_id: UUID
    device_public_ids: tuple[str, ...]
    divergent_fields: tuple[str, ...]
    # field_name -> hashes seguros (uno por perfil involucrado, en el mismo
    # orden que device_public_ids). Nunca contenido real.
    field_hashes: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class EquivalentProfileGroup:
    user_id: UUID
    device_public_ids: tuple[str, ...]


@dataclass
class PreflightReport:
    users_with_devices: int = 0
    devices_without_user: int = 0
    profiles_on_orphan_devices: int = 0
    users_with_zero_profiles: int = 0
    users_with_one_profile: int = 0
    users_with_multiple_profiles: int = 0
    equivalent_profile_groups: list[EquivalentProfileGroup] = field(default_factory=list)
    divergent_profile_groups: list[ProfileDivergence] = field(default_factory=list)
    soft_deleted_profiles: int = 0
    soft_deleted_devices: int = 0
    fk_inconsistencies: list[str] = field(default_factory=list)

    @property
    def has_blocking_divergence(self) -> bool:
        return bool(self.divergent_profile_groups)


class ProfileDivergenceDetected(RuntimeError):
    """Se detectaron EmergencyProfile divergentes para un mismo User.

    No contiene contenido médico: solo user_id, public_id de los devices
    involucrados y nombres de campos divergentes (más hashes seguros).
    """

    def __init__(self, report: PreflightReport) -> None:
        self.report = report
        summary = "; ".join(
            f"user={d.user_id} devices={d.device_public_ids} fields={d.divergent_fields}"
            for d in report.divergent_profile_groups
        )
        super().__init__(
            f"Divergent EmergencyProfile content detected for {len(report.divergent_profile_groups)} "
            f"user(s), aborting: {summary}"
        )


def run_preflight(bind) -> PreflightReport:
    """Inspecciona la DB y devuelve un PreflightReport. No escribe nada.

    `bind` acepta cualquier objeto SQLAlchemy 2.0-style con `.execute()` que
    hidrate instancias ORM (una `Session`, o una `Session` construida sobre la
    `Connection` de una migración vía `Session(bind=connection)`).
    """
    report = PreflightReport()

    devices = list(bind.execute(select(Device)).scalars().all())
    profiles = list(bind.execute(select(EmergencyProfile)).scalars().all())

    devices_by_id = {d.id: d for d in devices}

    report.devices_without_user = sum(1 for d in devices if d.user_id is None)
    report.soft_deleted_devices = sum(1 for d in devices if d.deleted_at is not None)
    report.soft_deleted_profiles = sum(1 for p in profiles if p.deleted_at is not None)

    profiles_by_user: dict[UUID, list[tuple[Device, EmergencyProfile]]] = {}
    orphan_profile_count = 0

    for profile in profiles:
        device = devices_by_id.get(profile.device_id)
        if device is None:
            report.fk_inconsistencies.append(
                f"emergency_profiles.id={profile.id} references missing "
                f"device_id={profile.device_id}"
            )
            continue

        if device.user_id is None:
            orphan_profile_count += 1
            continue

        if profile.deleted_at is not None:
            # Soft-deleted: ya contabilizado en soft_deleted_profiles arriba.
            # No participa en la comparación de equivalencia/divergencia del
            # usuario: un perfil retirado no representa el estado actual.
            continue

        profiles_by_user.setdefault(device.user_id, []).append((device, profile))

    report.profiles_on_orphan_devices = orphan_profile_count

    users_with_devices = {d.user_id for d in devices if d.user_id is not None}
    report.users_with_devices = len(users_with_devices)

    for user_id in users_with_devices:
        entries = profiles_by_user.get(user_id, [])

        if not entries:
            report.users_with_zero_profiles += 1
            continue

        if len(entries) == 1:
            report.users_with_one_profile += 1
            continue

        report.users_with_multiple_profiles += 1

        _first_device, first_profile = entries[0]
        divergent_fields: set[str] = set()
        for _device, profile in entries[1:]:
            divergent_fields.update(diff_fields(first_profile, profile))

        device_public_ids = tuple(d.public_id for d, _p in entries)

        if divergent_fields:
            sorted_fields = tuple(sorted(divergent_fields))
            field_hashes = {
                f: tuple(_safe_field_hash(p, f) for _d, p in entries) for f in sorted_fields
            }
            report.divergent_profile_groups.append(
                ProfileDivergence(
                    user_id=user_id,
                    device_public_ids=device_public_ids,
                    divergent_fields=sorted_fields,
                    field_hashes=field_hashes,
                )
            )
        else:
            report.equivalent_profile_groups.append(
                EquivalentProfileGroup(user_id=user_id, device_public_ids=device_public_ids)
            )

    return report


def assert_preflight_is_clean(report: PreflightReport) -> None:
    """Fail-fast: aborta si el preflight detectó perfiles divergentes."""
    if report.has_blocking_divergence:
        raise ProfileDivergenceDetected(report)
