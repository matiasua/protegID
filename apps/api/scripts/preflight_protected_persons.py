"""CLI read-only: corre los preflights de ProtectedPerson contra DATABASE_URL.

No escribe nada en la base de datos y nunca imprime contenido médico o PII
completo, solo el resumen agregado de cada reporte (ids de fila y hashes
seguros por campo divergente, nunca el contenido real).

Uso:
    DATABASE_URL=postgresql://... python scripts/preflight_protected_persons.py

Corre dos preflights independientes, ambos de solo lectura:
  - Bloque 3 (0011): agrupa por User vía device_id. Relevante antes de que
    protected_person_id exista/esté poblado.
  - Bloque 5 (0012): agrupa EmergencyProfile ACTIVOS por protected_person_id
    directamente - la precondición real que 0012 valida (NULL count, >1
    activo, equivalencia/divergencia entre ellos).

Puede ejecutarse antes de aplicar cualquiera de esas migraciones, incluyendo
(con cuidado) contra development, ya que es puramente de lectura.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.services.protected_person_preflight import (
    run_consolidation_preflight,
    run_preflight,
)


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
            report = run_preflight(session)
            consolidation_report = run_consolidation_preflight(session)
    finally:
        engine.dispose()

    print("=== ProtectedPerson preflight report (Bloque 3 / 0011) ===")
    print(f"users_with_devices:          {report.users_with_devices}")
    print(f"devices_without_user:        {report.devices_without_user}")
    print(f"profiles_on_orphan_devices:  {report.profiles_on_orphan_devices}")
    print(f"users_with_zero_profiles:    {report.users_with_zero_profiles}")
    print(f"users_with_one_profile:      {report.users_with_one_profile}")
    print(f"users_with_multiple_profiles:{report.users_with_multiple_profiles}")
    print(f"equivalent_profile_groups:   {len(report.equivalent_profile_groups)}")
    print(f"divergent_profile_groups:    {len(report.divergent_profile_groups)}")
    print(f"soft_deleted_profiles:       {report.soft_deleted_profiles}")
    print(f"soft_deleted_devices:        {report.soft_deleted_devices}")
    print(f"fk_inconsistencies:          {len(report.fk_inconsistencies)}")

    print("\n=== ProtectedPerson consolidation preflight (Bloque 5 / 0012) ===")
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

    if report.has_blocking_divergence:
        blocking = True
        print("\nBLOCKING (0011): divergent EmergencyProfile content found. Details:")
        for divergence in report.divergent_profile_groups:
            print(
                f"  user={divergence.user_id} "
                f"devices={divergence.device_public_ids} "
                f"fields={divergence.divergent_fields}"
            )

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
