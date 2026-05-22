"""Conexión y health check básico de PostgreSQL."""

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.settings import get_settings


def _get_database_url() -> str:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(_get_database_url(), pool_pre_ping=True)


def ping_database() -> bool:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))

    return True
