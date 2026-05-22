"""Readiness real para dependencias críticas."""

from collections.abc import Callable

from app.core.db import ping_database
from app.core.redis import ping_redis
from app.core.storage import check_bucket_access


DependencyCheck = Callable[[], bool]


def _run_check(check: DependencyCheck) -> str:
    try:
        return "ok" if check() else "error"
    except Exception:
        return "error"


def get_readiness_status() -> dict[str, object]:
    checks = {
        "database": _run_check(ping_database),
        "redis": _run_check(ping_redis),
        "minio": _run_check(check_bucket_access),
    }
    is_ready = all(status == "ok" for status in checks.values())

    return {
        "status": "ready" if is_ready else "unready",
        "ready": is_ready,
        "checks": checks,
    }
