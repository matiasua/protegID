"""Preflight de solo lectura para el bridge de datos hacia ProtectedPerson (Bloque 5).

Inspecciona el estado actual de EmergencyProfile sin escribir nada, y decide
si el estado de datos es seguro para la consolidación de la migración 0012
(protected_person_id NOT NULL + partial unique index de activos).

Regla central: fail-fast. Si un mismo ProtectedPerson tiene múltiples
EmergencyProfile activos (no soft-deleted) con contenido de dominio
divergente, este módulo lo reporta explícitamente. Nunca elige un perfil
"ganador", nunca fusiona.

Este módulo es reutilizable: puede invocarse de forma independiente (script,
test, chequeo manual contra development) pasando cualquier bind SQLAlchemy
2.0-style (`Session` o `Connection`) que soporte `.execute()`.

Bloque 8.6 retiró la mitad "Bloque 3" de este módulo (`run_preflight`, que
agrupaba EmergencyProfile por User vía `device_id`, pensada para auditar una
DB anterior a la migración 0011): esa columna fue eliminada en 0013 y la
migración 0011 ya corrió en toda DB de este linaje, así que no queda ningún
escenario legítimo para ejecutar ese chequeo. Ver docs/ai-rules.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select

from app.models import EmergencyProfile

# Campos que forman el contenido de DOMINIO de un EmergencyProfile: lo que
# realmente distingue "el mismo perfil" de "un perfil distinto". Deliberadamente
# excluidos de esta lista (no son contenido, son metadata de asociación/auditoría):
#   - id                    (identidad de fila, no de dominio)
#   - protected_person_id   (asociación C-lite, no contenido del perfil)
#   - created_at / updated_at (metadata de auditoría)
# deleted_at se trata explícitamente por separado (ver `run_consolidation_preflight`):
# un perfil soft-deleted NUNCA participa en la comparación de divergencia/
# equivalencia entre activos. No se ignora en silencio: se cuenta aparte
# (`historical_soft_deleted_profiles`).
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


# --- Preflight de solo lectura para 0012 (consolidate_active_ep / Bloque 5) ---
#
# Agrupa EmergencyProfile ACTIVOS directamente por protected_person_id, que es
# la precondición real que 0012 valida (NULL count, >1 activo, equivalencia).


@dataclass(frozen=True)
class ActiveProfileDivergence:
    protected_person_id: UUID
    profile_ids: tuple[UUID, ...]
    divergent_fields: tuple[str, ...]
    field_hashes: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class EquivalentActiveProfileGroup:
    protected_person_id: UUID
    profile_ids: tuple[UUID, ...]


@dataclass
class ConsolidationPreflightReport:
    protected_person_id_null_count: int = 0
    persons_with_one_active_profile: int = 0
    persons_with_multiple_active_profiles: int = 0
    equivalent_active_groups: list[EquivalentActiveProfileGroup] = field(default_factory=list)
    divergent_active_groups: list[ActiveProfileDivergence] = field(default_factory=list)
    historical_soft_deleted_profiles: int = 0

    @property
    def has_blocking_divergence(self) -> bool:
        return bool(self.divergent_active_groups)

    @property
    def is_safe_to_consolidate(self) -> bool:
        """True solo si 0012 puede correr sin fail-fast: sin NULLs y sin
        divergencia entre activos. No implica que no habrá consolidación
        (equivalent_active_groups puede ser no vacío: eso sí se resuelve
        automáticamente, de forma determinística)."""
        return self.protected_person_id_null_count == 0 and not self.has_blocking_divergence


def run_consolidation_preflight(bind) -> ConsolidationPreflightReport:
    """Inspecciona la DB y devuelve un ConsolidationPreflightReport. No
    escribe nada. Nunca imprime/incluye contenido médico completo: solo ids
    de fila y hashes seguros por campo divergente (ver `_safe_field_hash`).

    `bind` acepta cualquier objeto SQLAlchemy 2.0-style con `.execute()` que
    hidrate instancias ORM.
    """
    report = ConsolidationPreflightReport()

    profiles = list(bind.execute(select(EmergencyProfile)).scalars().all())

    report.protected_person_id_null_count = sum(
        1 for p in profiles if p.protected_person_id is None
    )
    report.historical_soft_deleted_profiles = sum(1 for p in profiles if p.deleted_at is not None)

    active_by_person: dict[UUID, list[EmergencyProfile]] = {}
    for profile in profiles:
        if profile.deleted_at is not None or profile.protected_person_id is None:
            continue
        active_by_person.setdefault(profile.protected_person_id, []).append(profile)

    for protected_person_id, entries in active_by_person.items():
        if len(entries) == 1:
            report.persons_with_one_active_profile += 1
            continue

        report.persons_with_multiple_active_profiles += 1

        first = entries[0]
        divergent_fields: set[str] = set()
        for other in entries[1:]:
            divergent_fields.update(diff_fields(first, other))

        profile_ids = tuple(sorted((p.id for p in entries), key=str))

        if divergent_fields:
            sorted_fields = tuple(sorted(divergent_fields))
            field_hashes = {
                f: tuple(_safe_field_hash(p, f) for p in entries) for f in sorted_fields
            }
            report.divergent_active_groups.append(
                ActiveProfileDivergence(
                    protected_person_id=protected_person_id,
                    profile_ids=profile_ids,
                    divergent_fields=sorted_fields,
                    field_hashes=field_hashes,
                )
            )
        else:
            report.equivalent_active_groups.append(
                EquivalentActiveProfileGroup(
                    protected_person_id=protected_person_id, profile_ids=profile_ids
                )
            )

    return report
