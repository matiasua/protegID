"""Resolución CANÓNICA de EmergencyProfile para un ProtectedPerson.

Post-0012, el invariante real de la base de datos es:

    MAX 1 EmergencyProfile ACTIVE (deleted_at IS NULL) por ProtectedPerson

(ver uq_emergency_profiles_active_protected_person, partial unique index).
Este módulo resuelve "el" perfil activo bajo ese invariante:

- 0 perfiles activos -> None.
- 1 perfil activo -> ese.
- >1 perfiles activos -> FAIL CLOSED. En una DB HEAD sana esto no puede
  ocurrir (el índice único lo impide); si ocurre, es una violación de
  integridad -- nunca se elige uno, nunca se reconcilia contenido médico.
"""

from app.models import EmergencyProfile, ProtectedPerson
from app.repositories.emergency_profiles import get_active_profiles_by_protected_person_id
from sqlalchemy.orm import Session


class CanonicalProfileDivergenceError(RuntimeError):
    """El ProtectedPerson tiene >1 EmergencyProfile activo. En una DB HEAD
    sana esto viola uq_emergency_profiles_active_protected_person y no
    debería poder ocurrir: es una corrupción de datos que requiere
    intervención manual, no una decisión automática. No se elige ninguno.

    El mensaje deliberadamente no incluye contenido médico/PII: solo ids de
    fila.
    """

    def __init__(self, protected_person_id, active_profile_ids):
        self.protected_person_id = protected_person_id
        self.active_profile_ids = active_profile_ids
        super().__init__(
            f"Multiple active EmergencyProfile rows for "
            f"protected_person_id={protected_person_id}: "
            f"profiles={active_profile_ids}"
        )


def _resolve_active_profile(
    session: Session, protected_person: ProtectedPerson
) -> EmergencyProfile | None:
    """Resuelve el único EmergencyProfile ACTIVE del ProtectedPerson.

    Fail closed (CanonicalProfileDivergenceError) si hay más de uno.
    """
    candidates = get_active_profiles_by_protected_person_id(
        session, protected_person.id
    )

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    raise CanonicalProfileDivergenceError(
        protected_person_id=protected_person.id,
        active_profile_ids=tuple(sorted(str(c.id) for c in candidates)),
    )


def get_canonical_emergency_profile(
    session: Session, protected_person: ProtectedPerson
) -> EmergencyProfile | None:
    return _resolve_active_profile(session, protected_person)


def get_active_profile_for_write(
    session: Session, protected_person: ProtectedPerson
) -> EmergencyProfile | None:
    """Usado exclusivamente por rutas de escritura (PUT). None si el
    ProtectedPerson todavía no tiene ningún EmergencyProfile activo (el
    caller debe crear uno). Fail closed (CanonicalProfileDivergenceError) si
    hay más de un perfil activo.
    """
    return _resolve_active_profile(session, protected_person)
