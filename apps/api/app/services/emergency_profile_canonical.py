"""Resolución CANÓNICA TRANSITORIA de EmergencyProfile para un ProtectedPerson.

TRANSITIONAL COMPATIBILITY LAYER: tras 0011 puede existir temporalmente más
de un EmergencyProfile activo para el mismo ProtectedPerson (uno por Device
legacy que apuntaba a perfiles equivalentes). Todavía no podemos aplicar
UNIQUE(protected_person_id) ni consolidar/eliminar duplicados (eso es un
bloque posterior), así que este módulo resuelve "el" perfil canónico:

- 0 perfiles activos -> None.
- 1 perfil activo -> ese.
- >1 perfiles activos:
    - si son equivalentes (mismo contenido de dominio) -> selección
      determinística (created_at ASC, id ASC como desempate estable). Esta
      selección NO implica que el elegido sea "más correcto": es solo un
      mecanismo transitorio porque ya se comprobó equivalencia.
    - si divergen -> FAIL CLOSED. Nunca se elige, nunca se reconcilia
      automáticamente.

Reutiliza (no duplica) la comparación de contenido de dominio de
app.services.protected_person_preflight, que ya es la fuente de verdad de
"qué campos son contenido" para este mismo propósito en el migration bridge.
"""

from app.models import EmergencyProfile, ProtectedPerson
from app.repositories.emergency_profiles import get_active_profiles_by_protected_person_id
from app.services.protected_person_preflight import diff_fields
from sqlalchemy.orm import Session


class CanonicalProfileDivergenceError(RuntimeError):
    """El ProtectedPerson tiene >1 EmergencyProfile activo con contenido
    divergente. No se elige ninguno: esto es una corrupción de datos que
    requiere intervención manual, no una decisión automática.

    El mensaje deliberadamente no incluye contenido médico/PII: solo ids de
    fila y nombres de campos divergentes.
    """

    def __init__(self, protected_person_id, divergent_profile_ids, divergent_fields):
        self.protected_person_id = protected_person_id
        self.divergent_profile_ids = divergent_profile_ids
        self.divergent_fields = divergent_fields
        super().__init__(
            f"Divergent canonical EmergencyProfile candidates for "
            f"protected_person_id={protected_person_id}: "
            f"profiles={divergent_profile_ids} fields={divergent_fields}"
        )


def _resolve_canonical_and_shadows(
    session: Session, protected_person: ProtectedPerson
) -> tuple[EmergencyProfile | None, list[EmergencyProfile]]:
    """Resuelve (canonical, shadows) entre los EmergencyProfile ACTIVE del
    ProtectedPerson. Fail closed (CanonicalProfileDivergenceError) si
    divergen; nunca elige, nunca reconcilia contenido médico.

    shadows es siempre [] cuando hay 0 o 1 candidatos activos.
    """
    candidates = get_active_profiles_by_protected_person_id(
        session, protected_person.id
    )

    if not candidates:
        return None, []
    if len(candidates) == 1:
        return candidates[0], []

    first = candidates[0]
    divergent_fields: set[str] = set()
    for other in candidates[1:]:
        divergent_fields.update(diff_fields(first, other))

    if divergent_fields:
        raise CanonicalProfileDivergenceError(
            protected_person_id=protected_person.id,
            divergent_profile_ids=tuple(sorted(str(c.id) for c in candidates)),
            divergent_fields=tuple(sorted(divergent_fields)),
        )

    canonical = min(candidates, key=lambda profile: (profile.created_at, profile.id))
    shadows = [candidate for candidate in candidates if candidate.id != canonical.id]
    return canonical, shadows


def get_canonical_emergency_profile(
    session: Session, protected_person: ProtectedPerson
) -> EmergencyProfile | None:
    canonical, _shadows = _resolve_canonical_and_shadows(session, protected_person)
    return canonical


def get_canonical_and_shadow_profiles_for_write(
    session: Session, protected_person: ProtectedPerson
) -> tuple[EmergencyProfile | None, list[EmergencyProfile]]:
    """TRANSITIONAL — remove after EmergencyProfile.protected_person_id becomes UNIQUE.

    Usado exclusivamente por rutas de escritura (PUT). Mientras pueda existir
    más de un EmergencyProfile activo equivalente para el mismo
    ProtectedPerson (duplicados legacy por-Device), toda escritura al
    canonical debe propagarse a sus shadows en la misma transacción, o
    produciríamos artificialmente divergencia (canonical != shadow) que el
    bloque de consolidación no podría distinguir de una divergencia médica
    real preexistente.

    Devuelve (canonical, shadows). canonical es None si el ProtectedPerson
    todavía no tiene ningún EmergencyProfile activo (el caller debe crear
    uno). Fail closed (CanonicalProfileDivergenceError) si los candidatos
    activos divergen: nunca se elige, nunca se reconcilia, nunca se escribe
    parcialmente.
    """
    return _resolve_canonical_and_shadows(session, protected_person)
