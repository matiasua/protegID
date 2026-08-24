"""CLI read-only: corre el preflight de consolidación de ProtectedPerson contra DATABASE_URL.

No escribe nada en la base de datos y nunca imprime contenido médico o PII
completo, solo el resumen agregado del reporte (ids de fila y hashes seguros
por campo divergente, nunca el contenido real).

Uso:
    DATABASE_URL=postgresql://... python scripts/preflight_protected_persons.py

Corre el preflight de Bloque 5 (0012): agrupa EmergencyProfile ACTIVOS por
protected_person_id directamente - la precondición real que 0012 valida (NULL
count, >1 activo, equivalencia/divergencia entre ellos). Puede ejecutarse
antes de aplicar esa migración, incluyendo (con cuidado) contra development,
ya que es puramente de lectura.

Bloque 8.6 retiró el preflight de Bloque 3 (0011, agrupaba por User vía
EmergencyProfile.device_id): esa columna fue eliminada en 0013 y 0011 ya
corrió en toda DB de este linaje, así que no queda ningún escenario legítimo
para ejecutarlo.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.services.protected_person_preflight import run_consolidation_preflight


def _database_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def main() -> None:
    engine = create_engine(_database_url())
    try:
        with Session(bind=engine) as session:
            consolidation_report = run_consolidation_preflight(session)
    finally:
        engine.dispose()

    print("=== ProtectedPerson consolidation preflight (Bloque 5 / 0012) ===")
    print(
        "protected_person_id_null_count:   "
        f"{consolidation_report.protected_person_id_null_count}"
    )
    print(
        "persons_with_one_active_profile:  "
        f"{consolidation_report.persons_with_one_active_profile}"
    )
    print(
        "persons_with_multiple_active:     "
        f"{consolidation_report.persons_with_multiple_active_profiles}"
    )
    print(f"equivalent_active_groups:         {len(consolidation_report.equivalent_active_groups)}")
    print(f"divergent_active_groups:          {len(consolidation_report.divergent_active_groups)}")
    print(
        "historical_soft_deleted_profiles: "
        f"{consolidation_report.historical_soft_deleted_profiles}"
    )

    blocking = False

    if consolidation_report.protected_person_id_null_count:
        blocking = True
        print(
            "\nBLOCKING (0012): "
            f"{consolidation_report.protected_person_id_null_count} emergency_profiles "
            "row(s) have protected_person_id IS NULL. Must be resolved before 0012 can run."
        )

    if consolidation_report.has_blocking_divergence:
        blocking = True
        print("\nBLOCKING (0012): divergent ACTIVE EmergencyProfile content found. Details:")
        for divergence in consolidation_report.divergent_active_groups:
            print(
                f"  protected_person_id={divergence.protected_person_id} "
                f"profiles={divergence.profile_ids} "
                f"fields={divergence.divergent_fields}"
            )

    if blocking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
