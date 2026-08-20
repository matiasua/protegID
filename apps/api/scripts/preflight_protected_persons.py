"""CLI read-only: corre el preflight de ProtectedPerson contra DATABASE_URL.

No escribe nada en la base de datos y nunca imprime contenido médico o PII
completo, solo el resumen agregado del PreflightReport.

Uso:
    DATABASE_URL=postgresql://... python scripts/preflight_protected_persons.py

Puede ejecutarse antes de la migración 0011, incluyendo (con cuidado) contra
development, ya que es puramente de lectura.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.services.protected_person_preflight import run_preflight


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
    finally:
        engine.dispose()

    print("=== ProtectedPerson preflight report ===")
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

    if report.has_blocking_divergence:
        print("\nBLOCKING: divergent EmergencyProfile content found. Details:")
        for divergence in report.divergent_profile_groups:
            print(
                f"  user={divergence.user_id} "
                f"devices={divergence.device_public_ids} "
                f"fields={divergence.divergent_fields}"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
